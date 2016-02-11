# coding=utf-8

"""	Permite crear una instancia que se encargara de proporcionar funciones
	facilitando el manejo del modem. Entre las funcionalidades basicas con
	las que cuenta, tenemos principalmente el envio y recepcion de mensajes
	SMS.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Miercoles 17 de Junio de 2015 """

import os
import json
import time
import copy
import shlex
import serial
import signal
import pickle
import inspect
import subprocess

import logger
import contactList
import messageClass

from curses import ascii # Para enviar el Ctrl-Z

JSON_FILE = 'config.json'
JSON_CONFIG = json.load(open(JSON_FILE))

class Modem(object):
	""" Clase 'Modem'. Permite la creacion de una instancia del dispositivo. """
	successfulConnection = None
	serialPort = None

	def __init__(self):
		""" Constructor de la clase 'Modem'. Utiliza la API 'pySerial' de
			Python para establecer un medio de comunicacion entre el usuario
			y el puerto donde se encuentra conectado el modem. Establece un
			'baudrate' y un 'timeout', donde este ultimo indica el intervalo
			de tiempo en segundos con el cual se hacen lecturas sobre el
			dispositivo. """
		self.modemInstance = serial.Serial()
		self.modemInstance.timeout = JSON_CONFIG["SMS"]["TIME_OUT"]
		self.modemInstance.baudrate = JSON_CONFIG["SMS"]["BAUD_RATE"]

	def sendAT(self, atCommand):
		""" Se encarga de enviarle un comando AT el modem. Espera la respuesta
			a ese comando, antes de continuar.
			@param atCommand: comando AT que se quiere ejecutar
			@type atCommand: str
			@return: respuesta del modem, al comando AT ingresado
			@rtype: list """
		self.modemInstance.write(atCommand + '\r')	 # Envio el comando AT al modem
		modemOutput = self.modemInstance.readlines() # Espero la respuesta
		# Verificamos si se produjo algún tipo de error relacionado con el comando AT
		for outputElement in modemOutput:
			if outputElement.startswith(('+CME ERROR', '+CMS ERROR')) and atCommand != 'AT+CNMA':
				outputElement = outputElement.replace('\r\n', '')
				logger.write('ERROR', '[SMS] %s.' % outputElement)
				raise
		return modemOutput

	def closePort(self):
		self.modemInstance.close()

class Sms(Modem):
	""" Subclase de 'Modem' correspondiente al modo de operacion con el que se va
		a trabajar. """
	isActive = False

	def __init__(self, _receptionBuffer):
		""" Constructor de la clase 'Sms'. Configura el modem para operar en modo mensajes
			de texto, indica el sitio donde se van a almacenar los mensajes recibidos,
			habilita notificacion para los SMS entrantes y establece el numero del centro
			de mensajes CLARO para poder enviar mensajes de texto (este campo puede variar
			dependiendo de la compania de telefonia de la tarjeta SIM). """
		Modem.__init__(self)
		self.receptionBuffer = _receptionBuffer

	def __del__(self):
		""" Destructor de la clase 'Modem'. Cierra la conexion establecida
			con el modem. """
		self.modemInstance.close()
		logger.write('INFO', '[SMS] Objeto destruido.')

	def connect(self, _serialPort):
		self.serialPort = _serialPort
		try:
			self.modemInstance.port = _serialPort
			self.modemInstance.open()
			#self.modemInstance.flushInput()
			#self.modemInstance.flushOutput()
			time.sleep(1.5)
			self.sendAT('ATZ')				 # Enviamos un reset
			self.sendAT('ATE1')				 # Habilitamos el echo
			self.sendAT('AT+CMEE=2')		 # Habilitamos reporte de error
			self.sendAT('AT+CMGF=1')		 # Establecemos el modo para sms
			self.sendAT('AT+CLIP=1')		 # Habilitamos identificador de llamada
			self.sendAT('AT+CNMI=1,2,0,0,0') # Habilito notificacion de mensaje entrante
			self.successfulConnection = True
			return True
		except:
			self.successfulConnection = False
			return False

	def receive(self):
		""" Funcion que se encarga consultar al modem por algun mensaje SMS entrante. Envia al
			mismo el comando AT que devuelve los mensajes de texto no leidos (que por ende seran
			los nuevos) y que en caso de obtenerlos, los envia de a uno al modulo de procesamiento
			para su examen. Si el remitente del mensaje se encuentra registrado (en el archivo
			'contactList') se procede a procesar el cuerpo del SMS, o en caso contrario, se envia
			una notificacion informandole que no es posible realizar la operacion solicitada.
			Tambien cada un cierto tiempo dado por el intervalo de temporizacion, envia a un numero
			de telefono dado por 'DESTINATION_NUMBER' un mensaje de actualizacion, que por el momento
			estara compuesto de un 'TimeStamp'. """
		smsAmount = 0
		callerID = None
		smsBodyList = list()
		smsHeaderList = list()
		unreadList = self.sendAT('AT+CMGL="REC UNREAD"')
		# Ejemplo de unreadList[0]: AT+CMGL="REC UNREAD"\r\r\n
		# Ejemplo de unreadList[1]: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
		# Ejemplo de unreadList[2]: Primer mensaje.\r\n
		# Ejemplo de unreadList[3]: +CMGL: 1,"REC UNREAD","+5493512560536",,"14/10/26,17:15:10-12"\r\n
		# Ejemplo de unreadList[4]: Segundo mensaje.\r\n
		# Ejemplo de unreadList[5]: \r\n
		# Ejemplo de unreadList[6]: OK\r\n
		for unreadIndex, unreadData in enumerate(unreadList):
			if unreadData.startswith('+CMGL'):
				smsHeaderList.append(unreadList[unreadIndex])
				smsBodyList.append(unreadList[unreadIndex + 1])
				smsAmount += 1
			elif unreadData.startswith('OK'):
				break
		# Ejemplo de smsHeaderList[0]: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
		# Ejemplo de smsBodyList[0]  : Primer mensaje.\r\n
		# Ejemplo de smsHeaderList[1]: +CMGL: 1,"REC UNREAD","+5493512560536",,"14/10/26,17:15:10-12"\r\n
		# Ejemplo de smsBodyList[1]  : Segundo mensaje.\r\n
		self.isActive = True
		while self.isActive:
			# Leemos los mensajes de texto recibidos...
			if smsAmount is not 0:
				logger.write('DEBUG', '[SMS] Ha(n) llegado ' + str(smsAmount) + ' nuevo(s) mensaje(s) de texto!')
				for smsHeader, smsBody in zip(smsHeaderList, smsBodyList):
					# Ejemplo smsHeader: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
					# Ejemplo smsBody  : Primer mensaje.\r\n
					# Ejemplo smsHeader: +CMT: "+543512641040",,"15/12/29,11:19:38-12"\r\n
					# Ejemplo smsBody  : Nuevo SMS.\r\n
					telephoneNumber = self.getTelephoneNumber(smsHeader) # Obtenemos el numero de telefono
					# Comprobamos si el remitente del mensaje (un teléfono) está registrado...
					if telephoneNumber in contactList.allowedNumbers.values() or not JSON_CONFIG["COMMUNICATOR"]["RECEPTION_FILTER"]:
						# Quitamos el '\r\n' del final y obtenemos el mensaje de texto
						smsMessage = smsBody.replace('\r\n', '')
						if smsMessage.startswith('INSTANCE'):
							# Quitamos la 'etiqueta' que hace refencia a una instancia de mensaje
							messageInstance = smsMessage[len('INSTANCE'):]
							# 'Deserializamos' la instancia de mensaje para obtener el objeto en sí
							messageInstance = pickle.loads(messageInstance)
							self.receptionBuffer.put((100 - messageInstance.priority, messageInstance))
						else: 
							self.receptionBuffer.put((10, smsMessage))
						#self.sendOutput(telephoneNumber, smsMessage) # -----> SOLO PARA LA DEMO <-----
						logger.write('INFO', '[SMS] Mensaje de ' + str(telephoneNumber) + ' recibido correctamente!')
					else:
						# ... caso contrario, verificamos si el mensaje proviene de la pagina web de CLARO o PERSONAL...
						if telephoneNumber == 876966 or telephoneNumber == 8235079297:
							logger.write('WARNING', '[SMS] No es posible procesar mensajes enviados desde la página web!')
						# ... sino, comunicamos al usuario que no se encuentra registrado.
						else:
							logger.write('WARNING', '[SMS] Imposible procesar una solicitud. El número no se encuentra registrado!')
							smsMessage = 'Imposible procesar la solicitud. Usted no se encuentra registrado!'
							#self.send(telephoneNumber, smsMessage)
					# Si el mensaje fue leído desde la memoria, entonces lo borramos
					if smsHeader.startswith('+CMGL'):
						# Obtenemos el índice del mensaje en memoria
						smsIndex = self.getSmsIndex(smsHeader.split(',')[0])
						# Eliminamos el mensaje desde la memoria porque ya fue leído
						self.removeSms(smsIndex)
					# Eliminamos la cabecera y el cuerpo del mensaje de las listas correspondientes
					smsHeaderList.remove(smsHeader)
					smsBodyList.remove(smsBody)
					# Decrementamos la cantidad de mensajes a procesar
					smsAmount -= 1
			elif self.modemInstance.inWaiting() is not 0:
				bytesToRead = self.modemInstance.inWaiting()
				receptionList = self.modemInstance.read(bytesToRead).split('\r\n')
				# Quitamos el primer y último elemento, porque no contienen información
				receptionList.pop(len(receptionList) - 1)
				receptionList.pop(0)
				# Ejemplo receptionList: ['+CMT: "+543512641040","","16/01/31,05:00:08-12"', 'Nuevo SMS.']
				# Ejemplo receptionList: ['RING', '', '+CLIP: "+543512641040",145,"",0,"",0']
				# Ejemplo receptionList: ['NO CARRIER']
				if receptionList[0].startswith('+CMT'):
					try:
						smsHeaderList.append(receptionList[0])
						smsBodyList.append(receptionList[1])
						self.sendAT('AT+CNMA') # Enviamos el ACK (ńecesario sólo para los Dongle USB)
					except:
						pass # La excepción aparece cuando el módem no soporta (no necesita) el ACK
					finally:
						smsAmount += 1
				elif receptionList[0].startswith('RING'):
					callerID = self.getTelephoneNumber(receptionList[2])
					logger.write('INFO', '[CALL] El número \'%s\' está llamando...' % callerID)
				elif receptionList[0].startswith('NO CARRIER'):
					logger.write('INFO', '[CALL] Llamada perdida de \'%s\'.' % callerID)
					callerID = None
			else:
				time.sleep(1)
		logger.write('WARNING', '[SMS] Función \'%s\' terminada.' % inspect.stack()[0][3])

	def send(self, messageToSend, telephoneNumber):
		""" Envia el comando AT correspondiente para enviar un mensaje de texto.
			@param telephoneNumber: numero de telefono del destinatario
			@type telephoneNumber: int
			@param messageToSend: mensaje de texto a enviar
			@type messageToSend: str """
		# Comprobación de envío de texto plano
		if isinstance(messageToSend, messageClass.SimpleMessage) and not messageToSend.isInstance:
			smsMessage = messageToSend.plainText
		# Entonces se trata de enviar una instancia de mensaje
		else:
			# Copiamos el objeto antes de borrar el campo 'isInstance', por un posible fallo de envío
			tmpMessage = copy.copy(messageToSend)
			# Eliminamos el último campo del objeto, ya que el receptor no lo necesita
			delattr(tmpMessage, 'isInstance')
			# Serializamos el objeto para poder transmitirlo
			smsMessage = 'INSTANCE' + pickle.dumps(tmpMessage)
		try:
			# Enviamos los comandos AT correspondientes para efectuar el envío el mensaje de texto
			self.sendAT('AT+CMGS="' + str(telephoneNumber) + '"') # Numero al cual enviar el Sms
			self.sendAT(smsMessage + ascii.ctrl('z')) 			  # Mensaje de texto terminado en Ctrl+Z
			logger.write('INFO', '[SMS] Mensaje de texto enviado a \'%s\'.' % str(telephoneNumber))
			# Borramos el mensaje enviado almacenado en la memoria
			self.removeAllSms()
			return True
		except:
			logger.write('WARNING', '[SMS] Error al enviar el mensaje de texto a \'%s\'.' % str(telephoneNumber))
			return False

	def sendCall(self, telephoneNumber):
		self.sendAT('ATD' + str(telephoneNumber) + ';') # Numero al cual se quiere llamar

	def hangUpCall(self):
		self.sendAT('ATH') # Cuelga la llamada en curso

	def removeSms(self, smsIndex):
		""" Envia el comando AT correspondiente para elimiar todos los mensajes del dispositivo.
			El comando AT tiene una serie de parametros, que dependiendo de cada uno de ellos
			indicara cual de los mensajes se quiere eliminar. En nuestro caso le indicaremos
			que elimine los mensajes leidos y los mensajes enviados, ya que fueron procesados
			y no los requerimos mas (ademas necesitamos ahorrar memoria, debido a que la misma
			es muy limitada). """
		self.sendAT('AT+CMGD=' + str(smsIndex)) # Elimina el mensaje especificado

	def removeAllSms(self):
		self.sendAT('AT+CMGD=1,2') # Elimina todos los mensajes leidos y enviados (1,4 es TODO)

	def getSmsIndex(self, atOutput):
		# Ejemplo de 'atOutput' (para un mensaje enviado) : +CMGS: 17
		# Ejemplo de 'atOutput' (para un mensaje recibido): +CMGL: 2
		# Quitamos el comando AT, dejando solamente el índice del mensaje en memoria
		if atOutput.startswith('+CMGS'):
			atOutput = atOutput.replace('+CMGS: ', '')
		elif atOutput.startswith('+CMGL'):
			atOutput = atOutput.replace('+CMGL: ', '')
		smsIndex = int(atOutput)
		return smsIndex

	def getTelephoneNumber(self, smsHeader):
		""" Procesa la cabecera del SMS.
			@return: numero de telefono del remitente
			@rtype: int """
		# Ejemplo de smsHeader recibido de un movil: +CLIP: "+543512641040",145,"",0,"",0']
		# Ejemplo de smsHeader recibido de un movil: +CMT: "+543512641040",,"15/12/29,11:41:23-12"\r\n
		# Ejemplo de smsHeader recibido de un movil: +CMGL: 0,"REC UNREAD","+5493512560536",,"14/10/26,17:12:04-12"\r\n
		# Ejemplo de smsHeader recibido de la web  : +CMGL: 2,"REC UNREAD","876966",,"14/10/26,19:36:42-12"\r\n
		headerList = smsHeader.split(',')		  # Separamos smsHeader por comas
		telephoneNumber = None
		if headerList[0].startswith(('+CLIP', '+CMT')):
			# Ejemplo de headerList[0]: +CMT: "+543512641040"
			# Ejemplo de headerList[0]: +CLIP: "+543512641040"
			telephoneNumber = headerList[0].split()[1].replace('"', '') # Quitamos las comillas
		elif headerList[0].startswith('+CMGL'):
			# Ejemplo de headerList[2]: "+5493512560536" | "876966"
			telephoneNumber = headerList[2].replace('"', '') # Quitamos las comillas
		# Ejemplo de telephoneNumber: +543512641040 | +5493512560536 | 876966
		if telephoneNumber.startswith('+549'):
			telephoneNumber = telephoneNumber.replace('+549', '') # Quitamos el codigo de pais
			# Ejemplo de telephoneNumber: 3512560536
		elif telephoneNumber.startswith('+54'):
			telephoneNumber = telephoneNumber.replace('+54', '') # Quitamos el codigo de pais
			# Ejemplo de telephoneNumber: 3512641040
		return int(telephoneNumber)

	def sendOutput(self, telephoneNumber, smsMessage):
		try:
			subprocess.Popen(['gnome-terminal', '-x', 'sh', '-c', smsMessage + '; exec bash'], stderr = subprocess.PIPE)
			#subprocess.check_output(shlex.split(smsMessage), stderr = subprocess.PIPE)
			smsMessage = 'El comando se ejecuto exitosamente!'
		except subprocess.CalledProcessError as e: # El comando es correcto pero le faltan parámetros
			smsMessage = 'El comando es correcto pero le faltan parámetros!'
		except OSError as e: # El comando no fue encontrado (el ejecutable no existe)
			smsMessage = 'El comando es incorrecto! No se encontró el ejecutable.'
		finally:
			#self.send(telephoneNumber, smsMessage)
			pass

class Gprs(Modem):

	pppInterface = None

	local_IP_Address = None
	remote_IP_Address = None
	primary_DNS_Address = None
	secondary_DNS_Address = None

	isActive = False

	def __init__(self): 
		Modem.__init__(self)

	def __del__(self):
		""" Destructor de la clase 'Modem'. Cierra la conexion establecida
			con el modem. """
		self.modemInstance.close()
		logger.write('INFO', '[GRPS] Objeto destruido.')

	def connect(self):
		try:
			ponProcess = subprocess.Popen('pon', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			ponOutput, ponError = ponProcess.communicate()
			# Si no se produjo ningún error, entonces se intenta iniciar la conexión con el APN
			if ponError == '':
				syslogFile = open('/var/log/syslog', 'a+')
				syslogFile.seek(0, 2) # Apuntamos al final del archivo
				while True:
					syslogOutput = syslogFile.readline()
					if syslogOutput.find('local  IP address ') > 0:
						# Se asignó una direccion IP...
						self.local_IP_Address = syslogOutput.split()[8]
						logger.write('DEBUG', '[GRPS] Dirección IP: %s' % self.local_IP_Address)
						continue
					elif syslogOutput.find('remote IP address ') > 0:
						# Se asignó una puerta de enlace...
						self.remote_IP_Address = syslogOutput.split()[8]
						logger.write('DEBUG', '[GRPS] Puerta de enlace: %s' % self.remote_IP_Address)
						continue
					elif syslogOutput.find('primary   DNS address ') > 0:
						# Se asignó un servidor DNS primario...
						self.primary_DNS_Address = syslogOutput.split()[8]
						logger.write('DEBUG', '[GRPS] DNS Primario: %s' % self.primary_DNS_Address)
						continue
					elif syslogOutput.find('secondary DNS address ') > 0:
						# Se asignó un servidor DNS secundario (último parámetro)...
						self.secondary_DNS_Address = syslogOutput.split()[8]
						logger.write('DEBUG', '[GRPS] DNS Secundario: %s' % self.secondary_DNS_Address)
						continue
					elif syslogOutput.find('Script /etc/ppp/ip-up finished') > 0:
						logger.write('DEBUG', '[GRPS] Parámetros de red configurados exitosamente!')
						self.isActive = True
						return True
					elif syslogOutput.find('Connection terminated') > 0:
						logger.write('DEBUG', '[GRPS] No se pudo establecer la conexión con la red GPRS!')
						return False
			# El puerto serial en '/etc/ppp/options-mobile' está mal configurado o no existe (desconectado)
			else:
				logger.write('WARNING', '[GRPS] No hay ningún módem conectado para realizar la conexión!')
		except:
			logger.write('ERROR', '[GRPS] Se produjo un error al intentar realizar la conexión!')
			return False

	def disconnect(self):
		try:
			poffProcess = subprocess.Popen('poff', stdout = subprocess.PIPE, stderr = subprocess.PIPE)
			poffOutput, poffError = poffProcess.communicate()
			if poffOutput.find('No pppd is running') > 0:
				logger.write('WARNING', '[GRPS] No hay ninguna conexión activa para desconectar!')
				return False
			else:
				logger.write('WARNING', '[GRPS] La conexión activa ha sido desconectada correctamente!')
				return True
		except:
			logger.write('ERROR', '[GRPS] Se produjo un error al intentar desconectar la conexión!')
			return False
 # coding=utf-8

"""	Modulo cuya finalidad es proporcionar funciones que se encarguen del envio
	y recepcion de paquetes de datos en la red local.
	@author: Gonzalez Leonardo Mauricio
	@author: Reinoso Ever Denis
	@organization: UNC - Fcefyn
	@date: Lunes 16 de Mayo de 2015 """

import contactList

import time
import socket
import threading

class Ethernet(object):

	sock = ''
	UDP_IP = "127.0.0.1"
	UDP_RECEPTION_PORT = 5014
	reciving = False
	receptionThread = ''
	receptionBuffer = list()
	processNotifications = True
	warningNotifications = True
	errorNotifications = True
	contRead = 0

	def __init__(self, _receptionBuffer, _processNotifications, _warningNotifications, _errorNotifications):
		"""Se crean los sockets para envío y recepción. Se activa el hilo para la recepción 
		y se asigna el buffer también para la recepción.
		@param _receptionBuffer: Buffer para la recepción de datos
		@type: list"""
		#print 'Configurando el modulo ETHERNET...'
		#socket.setdefaulttimeout(10)                                                   # Establecemos tiempo maximo antes de reintentar lectura
		self.receptionBuffer = _receptionBuffer
		self.processNotifications = _processNotifications
		self.warningNotifications = _warningNotifications
		self.errorNotifications = _errorNotifications
		self.sock = socket.socket(socket.AF_INET, # Internet
						socket.SOCK_DGRAM) # UDP
		self.receptionSock = socket.socket(socket.AF_INET, # Internet
						socket.SOCK_DGRAM) # UDP
		self.reciving = True
		self.receptionThread = threading.Thread(target = self.recievePacket, name = 'packetReciever')
		self.receptionThread.start()
		if (self.warningNotifications): print '[MODO ETHERNET] Listo para usarse.'

	def __del__(self):
		"""Elminación de la instancia de esta clase, cerrando conexiones establecidas, para no dejar
		puertos ocupados en el Host"""
		self.closeEthernet()
		if (self.warningNotifications): print '[MODO ETHERNET] Se terminó la sesión.'

	def closeEthernet(self):
		""" Finaliza la sesion iniciada, es decir que cierra los sockets para ethernet"""
		self.sock.close()
		self.receptionSock.close()

	def sendEthernetPacket(contact, message):
		if contactList.allowedIpAddress.has_key(contact):
			destinationIp = contactList.allowedIpAddress[contact]
			destinationPort = contactList.allowedPorts[contact]
			self.sock.sendto(message, (destinationIp, destinationPort))
			if (self.processNotifications): print '[MODO ETHERNET] Se envio un mensaje.'
	 	else:
			if (self.warningNotifications): print '[MODO ETHERNET] El contacto a enviar mensaje no esta configurado+.'

	def sendPacket(self, destinationIp, destinationPort, message):
		""" Envia una cadena de texto.
		@param detinationIP: dirección IP del destinatario
		@type emailDestination: str
		@param destinationPort: N° de puerto del destinatario
		@type destinationPort: int
		@param message: cadena de texto a enviar
		@type message: str """
		#print 'Parametros :' + message + destinationIp + str(destinationPort)
		self.sock.sendto(message, (destinationIp, destinationPort))
		if (self.processNotifications): print '[MODO ETHERNET] Se envio un mensaje.'

	def recievePacket(self):
		""" Esta función es ejecutada en un hilo, se queda esperando los paquetes
		que llegen al puerto establecido para guardarlos en el buffer."""
		if (self.processNotifications): print '[MODO ETHERNET] Se estan recibiendo paquetes.'
		try:
			self.receptionSock.bind((self.UDP_IP, self.UDP_RECEPTION_PORT))
		except Exception, e: #Selecciona el siguiente puerto en caso de estar ocupado
			newPort = self.UDP_RECEPTION_PORT + 1
			if (self.warningNotifications): print '[MODO ETHERNET] Puerto UDP de recepción en uso se cambia al ' + str(newPort)
			self.receptionSock.bind((self.UDP_IP, self.UDP_RECEPTION_PORT))
		self.receptionSock.settimeout(2)
		while self.reciving:
			try:
				data, addr = self.receptionSock.recvfrom(1024) # buffer size is 1024 bytes
				self.receptionBuffer.append(data)
			except Exception, e:
				pass
			#if data!=None:
  			#print "received message:", data
		if (self.warningNotifications): print '[MODO ETHERNET] Ya no se estan recibiendo paquetes.'
	
	def stopReception(self):
		"""Se termina la ejecución del hilo cambiando su condición de ejecución."""
		self.reciving = False
		#time.sleep(6)
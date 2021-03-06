# coding=utf-8

import os
import sys
import termios

import contactList
import communicator
import messageClass

def main():
	endMain = False
	os.system('clear')

	print '----------- MODULO DE COMUNICACION -----------\n'
	print '\t\t1 - Enviar mensaje/archivo'
	print '\t\t2 - Enviar instancia de mensaje'
	print '\t\t3 - Leer un mensaje'
	print '\t\t4 - Llamar a un número'
	print '\t\t5 - Atender la llamada'
	print '\t\t6 - Colgar la llamada'
	print '\t\t7 - Conectar GPRS'
	print '\t\t8 - Desconectar GPRS'
	print '\t\tq - Salir'
	print '\t\to - DEBUG: Abrir Comunicador'
	print '\t\tc - DEBUG: Cerrar Comunicador\n'

	communicator.open()

	while not endMain:
		try:
			termios.tcflush(sys.stdin, termios.TCIOFLUSH) # Limpiamos el stdin
			optionSelected = raw_input()
			# Opcion 1 - Enviar mensaje
			if optionSelected is '1':
				# Preguntamos si se desea ver una lista con los clientes registrados
				selectClient = askClients()
				if selectClient is None:
					print 'Abortado.'
					continue
				# Indicamos el cliente al cual se va a enviar el mensaje
				receiver = raw_input('Cliente a enviar: ')
				# Indicamos el mensaje que se desea enviar
				messageToSend = raw_input('Mensaje a enviar: ')
				# Preguntamos si hay alguna preferencia en relación a los medios de comunicación
				selectMedia = askMedia()
				if selectMedia is True:
					# El medio preferido está dado por 'media'
					media = raw_input('Medio de comunicación preferido: ')
					communicator.send(messageToSend, receiver, media) # <----- IMPORTANTE
				elif selectMedia is False:
					# El medio se elige automáticamente
					communicator.send(messageToSend, receiver) # <----- IMPORTANTE
				else:
					print 'Abortado.'
					continue
			# Opcion 2 - Enviar instancia de mensaje
			elif optionSelected is '2':
				# Establecemos el campo 'sender'
				sender = raw_input('Nombre del emisor: ')
				# Preguntamos si se desea ver una lista con los clientes registrados
				selectClient = askClients()
				if selectClient is None:
					print 'Abortado.'
					continue
				# Establecemos el campo 'receiver'
				receiver = raw_input('Cliente a enviar: ')
				# Establecemos el campo 'infoText'
				infoText = raw_input('Mensaje a enviar: ')
				# Creamos la instancia de mensaje
				infoMessage = messageClass.InfoMessage(sender, receiver, infoText)
				# Preguntamos si hay alguna preferencia en relación a los medios de comunicación
				selectMedia = askMedia()
				if selectMedia is True:
					# El medio preferido está dado por 'media'
					media = raw_input('Medio de comunicación preferido: ')
					communicator.send(infoMessage, media = media) # <----- IMPORTANTE
				elif selectMedia is False:
					# El medio se elige automáticamente
					communicator.send(infoMessage) # <----- IMPORTANTE
				else:
					print 'Abortado.'
					continue
			# Opcion 3 - Leer un mensaje
			elif optionSelected is '3':
				messageReceived = communicator.receive()
				if messageReceived is not None:
					if isinstance(messageReceived, messageClass.Message):
						print 'Instancia de mensaje recibida: ' + str(messageReceived)
						print '\tPrioridad: ' + str(messageReceived.priority)
						print '\tEmisor: ' + messageReceived.sender
						if isinstance(messageReceived, messageClass.InfoMessage):
							print '\tMensaje de texto: ' + str(messageReceived.infoText)
					else:
						print 'Mensaje recibido: %s' % messageReceived
			# Opcion 4 - Llamar a un número
			elif optionSelected is '4':
				# Indicamos el número al cual efectuar la llamada de voz
				telephoneNumber = raw_input('Número a llamar: ')
				communicator.sendVoiceCall(telephoneNumber)
			# Opcion 5 - Atender la llamada
			elif optionSelected is '5':
				communicator.answerVoiceCall()
			# Opcion 6 - Colgar la llamada
			elif optionSelected is '6':
				communicator.hangUpVoiceCall()
			# Opcion 7 - Conectar GPRS
			elif optionSelected is '7':
				communicator.connectGprs()
			# Opcion 8 - Desconectar GPRS
			elif optionSelected is '8':
				communicator.disconnectGprs()
			elif optionSelected is 'q':
				endMain = True
			elif optionSelected is 'o':
				communicator.open()
			elif optionSelected is 'c':
				communicator.close()
			# Opcion inválida
			else:
				print 'Opción inválida!'
		except KeyboardInterrupt:
			endMain = True

	communicator.close()
	
	print '\n---------------- UNC - Fcefyn ----------------'
	print '---------- Ingeniería en Computación ---------'

def askClients():
	showClients = raw_input('¿Desea ver los clientes registrados? [S/n] ')
	if showClients is 'S' or showClients is 's' or len(showClients) is 0:
		# Creamos una lista de claves (clientes registrados en los diccionarios)
		clientList = list() + contactList.allowedHosts.keys()
		clientList += contactList.allowedMacAddress.keys()
		clientList += contactList.allowedEmails.keys()
		clientList += contactList.allowedNumbers.keys()
		# Quitamos los clientes repetidos
		clientList = list(set(clientList))
		print clientList
		return True
	elif showClients is 'N' or showClients is 'n':
		return False
	else:
		return None

def askMedia():
	selectMedia = raw_input('¿Desea elegir un medio de comunicación preferido? [S/n] ')
	if selectMedia is 'S' or selectMedia is 's' or len(selectMedia) is 0:
		print 'Lista de medios: GSM, GPRS, WIFI, BLUETOOTH, EMAIL, '
		return True
	elif selectMedia is 'N' or selectMedia is 'n':
		return False
	else:
		return None

if __name__ == '__main__':
	main() 

import threading
import bluetooth
import Queue

# Tamano del buffer en bytes (cantidad de caracteres)
BUFFER_SIZE = 1024

class BluetoothReader(threading.Thread):

	killReaderThread = False
	receptionBuffer = Queue.Queue()

	def __init__(self, _threadName, _remoteSocket, _receptionBuffer):
		threading.Thread.__init__(self, name = _threadName)
		self.remoteSocket = _remoteSocket
		self.receptionBuffer = _receptionBuffer

	def run(self):
		while not self.killReaderThread:
			try:
				''' Operacion bloqueante, que espera recibir al menos un byte o hasta que el extremo remoto este cerrado.
					Cuando el otro extremo este desconectado y todos los caracteres hayan sido leidos, la funcion retorna
					una cadena vacia. '''
				dataReceived = self.remoteSocket.recv(BUFFER_SIZE)
				if dataReceived == 'END':
					self.killReaderThread = True
				else:
					self.receptionBuffer.put(dataReceived)
					print '[BLUETOOTH] \'%s\': %s' % (self.getName(), dataReceived)
			except bluetooth.BluetoothError:
				pass
		# Cierra la conexion del socket cliente
		self.remoteSocket.close()
		print '[BLUETOOTH] \'%s\' terminado y cliente desconectado.' % self.getName()

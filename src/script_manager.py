import os
from entry import ConfEntry

class ScriptManage:

	def __init__(self, scriptDir, scriptSuffix, logger, opType = "run"):
		#check script folder
		self.scriptDir = scriptDir
		self.scriptSuffix = scriptSuffix
		self.logger = logger

		if not os.path.exists(scriptDir):
			os.makedirs(scriptDir)
		self.statusMap = dict()
		self.opType = opType
		self.getAllScripts(scriptDir)

	def getAllScripts(self, dirName):
		pathDirs = os.listdir(dirName)
		for pathDir in pathDirs:
			child = os.path.join(dirName, pathDir)
			if os.path.isdir(child):
				self.getAllScripts(child)
			else:
				if not pathDir.endswith(self.scriptSuffix):
					continue
				# if not child in self.statusMap.keys():
				# 	self.statusMap[child] = False
				confEntry = ConfEntry(self.scriptDir, "./", False, self.logger, child)
				self.statusMap[child] = confEntry.isFinished()

	def getSortedKeyValue(self):
		self.statusMap.clear()
		self.getAllScripts(self.scriptDir)
		keys = self.statusMap.keys()
		keys.sort()
		values = map(self.statusMap.get, keys)
		return (keys, values)

	def printScriptsState(self):
		keys = None
		status = None
		(keys, status) = self.getSortedKeyValue()
		statusStr = "All scripts status:\n"
		unfinished = 0
		for i in range(len(keys)):
			if status[i] == False:
				unfinished += 1
			# statusStr += "\tscript: %s, state: %s\n" % (keys[i], str(status[i]))
		statusStr += "\t total " + str(len(keys)) + ", left " + str(unfinished) + "\n"
		self.logger.info(statusStr)


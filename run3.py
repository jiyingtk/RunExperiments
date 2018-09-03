import re
import os
import sys
import time
import logging
import ConfigParser

scriptDir = "../scripts3"
resultDir = "../result"
logFile = "../run.log"
waitTime = 2
dbg = False
forceDeleteDB = False

logger = logging.getLogger("run-experiments")
logger.setLevel(logging.DEBUG)
fh = logging.FileHandler(logFile)
fh.setLevel(logging.DEBUG)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:\n\t%(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
logger.addHandler(fh)
logger.addHandler(ch)

def transSize(inStr):
	inStr = inStr.lower()
	patt = r"(\d+)(\D+)"
	m = re.match(patt, inStr)
	if not m:
		return 0
	else:
		size = int(m.group(1))
		if m.group(2) == "b":
			return size
		elif m.group(2) == "kb":
			return size * 1024
		elif m.group(2) == "mb":
			return size * 1024 * 1024
		elif m.group(2) == "gb":
			return size * 1024 * 1024
		else:
			logger.error("transSize string:" + inStr + " error")
			return 0

class MyConfigParser(ConfigParser.ConfigParser):
	def __init__(self, defaults = None):
		ConfigParser.ConfigParser.__init__(self, defaults = None)
	def optionxform(self, optionstr):
		return optionstr


class ConfEntry:
	def __init__(self, fileName = None):
		self.conf = MyConfigParser()
		self.fileName = fileName
		if fileName != None:
			self.loadFile(fileName)

	def loadFile(self, fileName):
		self.conf.read(fileName)

	def loadWorkload(self):
		workloadFile = self.conf.get("workload", "workloadFile")
		
		wlItems = self.conf.items("workload")
		wlItems = dict(wlItems)
		contents = []

		if self.conf.get("ycsb", "loadOrRun") == "load":
			wlItems["operationcount"] = 0
		if self.conf.get("ycsb", "loadOrRun").find("load") != -1:
			wlItems["insertstart"] = 0

		for key in wlItems:
			contents.append("%s=%s\n" % (key, wlItems[key]))
		f = open(workloadFile, "w+")
		f.writelines(contents)
		f.close()
		return True

	def setDBConfig(self):
		dbConfigFile = self.conf.get("global", "dbConfigFile")
		logger.debug("dbConfigFile: " + dbConfigFile)
		dbConfig = MyConfigParser()
		# dbConfig.read(dbConfigFile)

		if not dbConfig.has_section("basic"):
			dbConfig.add_section("basic")
		if not dbConfig.has_section("LRU"):
			dbConfig.add_section("LRU")

		defaultSections = ["basic-default", "LRU-default", "basic-modify", "LRU-modify"]
		for defaultSection in defaultSections:
			opvs = self.conf.items(defaultSection)
			for opv in opvs:
				if defaultSection.startswith("basic"):
					curSec = "basic"
				else:
					curSec = "LRU"
				dbConfig.set(curSec, opv[0], opv[1])

		tableSize = self.conf.get("ycsb", "tableSize")
		dbConfig.set("basic", "maxFileSize", transSize(tableSize))
		blockCacheSize = self.conf.get("ycsb", "blockCacheSize")
		dbConfig.set("basic", "blockCacheSize", transSize(blockCacheSize))
		regionDivideSize = self.conf.get("ycsb", "regionDivideSize")
		dbConfig.set("basic", "regionDivideSize", transSize(regionDivideSize))
		valueSize = self.conf.get("ycsb", "valueSize")
		dbConfig.set("basic", "valueSize", transSize(valueSize))

		DisableCompaction = self.conf.get("ycsb", "disableCompaction")
		dbConfig.set("basic", "forceDisableCompactionFlag", DisableCompaction)
		bitsArray = self.conf.get("ycsb", "arrayName")
		bitsArrayPath = self.conf.get("global", "bitsArrayPath")
		dbConfig.set("basic", "bitsArrayFileName", os.path.join(bitsArrayPath, "bitsArray" + bitsArray + ".txt"))

		with open(dbConfigFile,"w+") as f:
			dbConfig.write(f)

	def setOutputFile(self):
		if not os.path.exists(resultDir):
			os.makedirs(resultDir)
		scriptname = self.conf.get("global", "scriptName")
		curTime = time.strftime('%Y-%m-%d-%H-%M', time.localtime(time.time()))
		resultLoc = os.path.join(resultDir, scriptname + "--" + curTime)
		self.conf.set("status", "resultLoc", resultLoc)
		self.conf.set("status", "mainResultFile", "result.txt")

	def getDBFileName(self):
		databasepath = self.conf.get("global", "databasePath")
		dbFileName = self.conf.get("global", "dbNamePrefix")
		dbFileName += "l" + self.conf.get("basic-modify", "level")
		dbFileName += "s" + self.conf.get("basic-modify", "sizeRatio")
		dbFileName += "b" + self.conf.get("basic-modify", "bloomBits")
		dbFileName += "a" + self.conf.get("ycsb", "arrayName")
		dbFileName += "db" + self.conf.get("ycsb", "dbSize")
		dbFileName += "table" + self.conf.get("ycsb", "tableSize")
		dbFileName += "kv" + self.conf.get("ycsb", "valueSize")
		dbFileName = os.path.join(databasepath, dbFileName)
		logger.debug("dbFileName: " + dbFileName)
		return dbFileName

	def execScript(self):
		sections = self.conf.sections()
		if "global" not in sections:
			logger.warning("script file " + self.fileName + " not contains global section")
			return

		if self.conf.getboolean("status", "hasRun") == True:
			logger.info("script: " + self.fileName + " has run")
			return

		cmd = ""
		execFile = self.conf.get("global", "execFile")
		cmd += execFile + " "

		db = self.conf.get("ycsb", "db")
		cmd += "-db " + db + " "

		threads = self.conf.get("ycsb", "threads")
		cmd += "-threads " + threads + " "

		if not self.loadWorkload():
			return
		cmd += "-P " + self.conf.get("workload", "workloadFile") + " "

		dbFileName = self.getDBFileName()
		cmd += "-dbfilename " + dbFileName + " "

		if forceDeleteDB:
			if os.path.exists(dbFileName):
				logger.info("DB exists: " + dbFileName + ", force delete it")
				os.system("rm -rf " + dbFileName)
				flag = os.path.exists(dbFileName)
				logger.info("delete old db: " + str(flag))

		self.setDBConfig()
		configpath = self.conf.get("global", "dbConfigFile")
		cmd += "-configpath " + configpath + " "

		loadorrun = self.conf.get("ycsb", "loadOrRun")
		if loadorrun == "run":
			cmd += "-skipLoad true "
		else:
			cmd += "-skipLoad false "

		readTheadNums = self.conf.get("ycsb", "readThreadNums")
		cmd += "-readTheadNums " + readTheadNums + " "

		self.setOutputFile()
		mainResultFile = self.conf.get("status", "mainResultFile")
		cmd += "> " + mainResultFile + " 2>&1"

		logger.info("cmd: " + cmd)

		os.system(cmd)

		self.clean()

	def clean(self):
		endshell = self.conf.get("global", "endShell")
		os.system(endshell)

		resultLoc = self.conf.get("status", "resultLoc")
		if os.path.exists(resultLoc):
			logger.error("result folder exists: " + resultLoc)
			resultLoc += " (2)"
			self.conf.set("status", "resultLoc", resultLoc)

		insertproportion = self.conf.getfloat("workload", "insertproportion")
		if insertproportion != 0:
			recordcount = self.conf.getint("workload", "recordcount")
			operationcount = self.conf.getint("workload", "operationcount")
			newrecordcount = int(recordcount + operationcount * insertproportion)
			self.conf.set("workload", "recordcount", newrecordcount)
			self.conf.set("workload", "insertstart", newrecordcount)
			logger.info("insert new data, change recordcount and insertstart from " + str(recordcount) + " to " + str(newrecordcount))

		os.makedirs(resultLoc)

		self.conf.set("status", "hasRun", "true")
		with open(self.fileName,"w+") as f:
			self.conf.write(f)
		
		os.system("cp " + self.fileName + " " + resultLoc)
		os.system("mv ./* " + resultLoc)
		os.system("chown kv-group " + resultLoc)
		os.system("chmod +r " + resultLoc + "/*")




class ScriptManage:
	opTypes = ["run", "result"]

	def __init__(self, opType = "run"):
		#check script folder
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
				if not child in self.statusMap.keys():
					self.statusMap[child] = False

	def getSortedKeyValue(self):
		self.getAllScripts(scriptDir)
		keys = self.statusMap.keys()
		keys.sort()
		values = map(self.statusMap.get, keys)
		return (keys, values)

	def printScriptsState(self):
		keys = None
		status = None
		(keys, status) = self.getSortedKeyValue()
		statusStr = "All scripts status:\n"
		for i in range(len(keys)):
			statusStr += "\tscript: %s, state: %s\n" % (keys[i], str(status[i]))
		logger.info(statusStr)

	def checkUlimit(self):
		with os.popen("ulimit -n") as p:
			line  = p.readline().strip()
			if int(line) < 60000:
				logger.error("system max open file nums too small: " + line)
				return False
			else:
				logger.info("system max open file nums: " + line)
				return True

	def checkCurWorkspace(self):
		if len(os.listdir("./")) != 0:
			logger.error("current folder not empty!")
			return False
		else:
			return True


	def process(self):
		if not self.checkUlimit():
			return
		keys = None
		status = None
		while True:
			(keys, status) = self.getSortedKeyValue()
			i = 0
			while i < len(keys):
				if status[i] == False:
					break
				i += 1
			if i == len(keys):
				break

			if not dbg and not self.checkCurWorkspace():
				break

			if self.opType == "run":
				logger.info("process script: " + keys[i])
				confEntry = ConfEntry(keys[i])
				confEntry.execScript()
				self.statusMap[keys[i]] = True
			
			self.printScriptsState()
			time.sleep(waitTime)


if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == '-d':
		dbg = True
	if len(sys.argv) > 1 and sys.argv[1] == '-f':
		forceDeleteDB = True
	scriptManage = ScriptManage() 	
	scriptManage.process()

import os
import re
import time
import ConfigParser


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
			return size * 1024 * 1024 * 1024
		else:
			logger.error("transSize string:" + inStr + " error")
			return 0



class MyConfigParser(ConfigParser.ConfigParser):
	def __init__(self, defaults = None):
		ConfigParser.ConfigParser.__init__(self, defaults = None)
	def optionxform(self, optionstr):
		return optionstr


class ConfEntry:
	def __init__(self, scriptDir, resultDir, forceDeleteDB, logger, fileName = None):
		self.scriptDir = scriptDir
		self.resultDir = resultDir
		self.forceDeleteDB = forceDeleteDB
		self.logger = logger
		self.conf = MyConfigParser()
		self.fileName = fileName
		if fileName != None:
			self.loadFile(fileName)

	def loadFile(self, fileName):
		self.conf.read(fileName)

	def isFinished(self):
		return self.conf.getboolean("status", "hasRun")

	def loadWorkload(self):
		if self.conf.getboolean("global", "needExtractRawDB"):
			recordcountbackup = self.conf.get("workload", "recordcountbackup")
			self.conf.set("workload", "recordcount", recordcountbackup)
			self.conf.set("workload", "insertstart", recordcountbackup)

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
		self.logger.debug("dbConfigFile: " + dbConfigFile)
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
		if not os.path.exists(self.resultDir):
			os.makedirs(self.resultDir)
		# scriptName = self.conf.get("global", "scriptName")
		scriptName = self.fileName
		if scriptName.endswith(".ini"):
			scriptName = scriptName[:-4]

		curTime = time.strftime('%Y-%m-%d-%H-%M', time.localtime(time.time()))
		scriptName = scriptName + "--" + curTime
		# resultLoc = os.path.join(resultDir, scriptName)
		resultLoc = scriptName.replace(self.scriptDir, self.resultDir)
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
		self.logger.debug("dbFileName: " + dbFileName)
		return dbFileName

	def execScript(self):
		sections = self.conf.sections()
		if "global" not in sections:
			self.logger.warning("script file " + self.fileName + " not contains global section")
			return

		if self.conf.getboolean("status", "hasRun") == True:
			self.logger.info("script: " + self.fileName + " has run")
			with open(self.fileName,"w+") as f:
				self.conf.write(f)
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

		if self.forceDeleteDB:
			if os.path.exists(dbFileName):
				self.logger.info("DB exists: " + dbFileName + ", force delete it")
				os.system("rm -rf " + dbFileName)

		if self.conf.getboolean("global", "needExtractRawDB"):
			self.logger.info("extract raw db to " + dbFileName)
			if os.path.exists(dbFileName):
				self.logger.info("DB exists: " + dbFileName + ", force delete it")
				os.system("rm -rf " + dbFileName)
				flag = os.path.exists(dbFileName)
				self.logger.info("delete old db, still exists: " + str(flag))
			rawDBPath = self.conf.get("global", "rawDBPath")
			if not os.path.exists(rawDBPath):
				self.logger.error("raw db not exists: " + rawDBPath)
				return
			extractCMD = "tar zxf " + rawDBPath + " -C " + self.conf.get("global", "databasePath")
			self.logger.info("exec: " + extractCMD)
			os.system(extractCMD)

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

		self.logger.info("cmd: " + cmd)

		os.system(cmd)

		self.clean()

	def clean(self):
		endshell = self.conf.get("global", "endShell")
		os.system(endshell)

		resultLoc = self.conf.get("status", "resultLoc")
		if os.path.exists(resultLoc):
			self.logger.error("result folder exists: " + resultLoc)
			resultLoc += "_(2)"
			self.conf.set("status", "resultLoc", resultLoc)

		insertproportion = self.conf.getfloat("workload", "insertproportion")
		if insertproportion != 0 and self.conf.get("ycsb", "loadOrRun") != "load":
			recordcount = self.conf.getint("workload", "recordcount")
			operationcount = self.conf.getint("workload", "operationcount")
			newrecordcount = int(recordcount + operationcount * insertproportion)
			self.conf.set("workload", "recordcount", newrecordcount)
			self.conf.set("workload", "insertstart", newrecordcount)
			self.logger.info("insert new data, change recordcount and insertstart from " + str(recordcount) + " to " + str(newrecordcount))

		os.makedirs(resultLoc)

		if resultLoc.find("/") != -1:
			parentDir = resultLoc[: resultLoc.find("/")]
			os.system("chown kv-group " + parentDir + " -R")

		self.conf.set("status", "hasRun", "true")
		with open(self.fileName,"w+") as f:
			self.conf.write(f)
		
		os.system("cp " + self.fileName + " " + resultLoc)
		os.system("mv ./* " + resultLoc)
		# os.system("chown kv-group " + resultLoc)
		os.system("chmod +r " + resultLoc + "/*")
 

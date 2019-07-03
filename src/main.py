import re
import os
import sys
import time
import logging
import entry
import script_manager


scriptDir = "../scripts"
resultDir = "../result"
logFile = "../run.log"
scriptSuffix = ".ini"
waitTime = 0.1
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





def checkUlimit():
	with os.popen("ulimit -n") as p:
		line  = p.readline().strip()
		if int(line) < 60000:
			logger.error("system max open file nums too small: " + line + ", please run `ulimit -HSn 100000`")
			return False
		else:
			logger.info("system max open file nums: " + line)
			return True

def checkCurWorkspace():
	if len(os.listdir("./")) != 0:
		logger.error("current folder not empty!")
		return False
	else:
		return True


def process():
	scriptManage = script_manager.ScriptManage(scriptDir, scriptSuffix, logger) 	

	if not checkUlimit():
		return
		
	keys = None
	status = None
	while True:
		(keys, status) = scriptManage.getSortedKeyValue()
		i = 0
		while i < len(keys):
			if status[i] == False:
				break
			i += 1
		if i == len(keys):
			break

		if not dbg and not checkCurWorkspace():
			break

		if scriptManage.opType == "run":
			logger.info("process script: " + keys[i])
			confEntry = entry.ConfEntry(scriptDir, resultDir, forceDeleteDB, logger, keys[i])
			confEntry.execScript()
			scriptManage.statusMap[keys[i]] = True
		
		scriptManage.printScriptsState()

		time.sleep(waitTime)



if __name__ == '__main__':
	if len(sys.argv) > 1 and sys.argv[1] == '-d':
		dbg = True
	if len(sys.argv) > 1 and sys.argv[1] == '-f':
		forceDeleteDB = True
	process()

import xml.etree.ElementTree as ET
import ConfigParser
import os
import sys
from optparse import OptionParser

modelScriptName = ""
scriptSuffix = ".ini"


no_registered_keys = dict()
def set_confs(confs, key, value):
	key_map = {

		"dbNamePrefix" : "global.dbNamePrefix",
		"databasePath" : "global.databasePath",
		"execFile" : "global.execFile",
		"needExtractRawDB" : "global.needExtractRawDB",
		"rawDBPath" : "global.rawDBPath",

		"hasRun" : "status.hasRun",
		"db" : "ycsb.db",
		"threads" : "ycsb.threads",
		"blockCache" : "ycsb.blockCacheSize",
		"disableCompaction" : "ycsb.disableCompaction",
		"regionDivideSize" : "ycsb.regionDivideSize",
		"threadnum" : "ycsb.threads",
		"regionSize" : "ycsb.regionDivideSize",
		"valueSize" : "ycsb.valueSize",
		"dbSize" : "ycsb.dbSize",
		"arrayName" : "ycsb.arrayName",

		"maxOpenFiles" : "basic-modify.maxOpenFiles",
		"useLRUCache" : "basic-modify.useLRUCache",
		"directIOFlag" : "basic-modify.directIOFlag",
		"forceDeleteLevel0File" : "basic-modify.forceDeleteLevel0File",
		"lifeTime" : "LRU-modify.lifeTime",
		"initFilterNum" : "LRU-modify.initFilterNum",

		"zipfianconst" : "workload.zipfianconst",
		"operationcount" : "workload.operationcount",
		"zerolookup" : "workload.zerolookuprate",
		"recordcount" : "workload.recordcount",
		"recordcountbackup" : "workload.recordcountbackup",
		"insertstart" : "workload.insertstart",
		"readproportion" : "workload.readproportion",
		"updateproportion" : "workload.updateproportion",
		"scanproportion" : "workload.scanproportion",
		"insertproportion" : "workload.insertproportion",
		"readmodifywriteproportion" : "workload.readmodifywriteproportion",
		"skipratioinload" : "workload.skipratioinload",
		"requestdistribution" : "workload.requestdistribution",
		"fieldlength" : "workload.fieldlength",
		"adjustfilter" : "workload.adjustfilter",

	}

	if key not in key_map:
		if key not in no_registered_keys:
			print("warning: " + key + " is not registered!")
			no_registered_keys[key] = 1
		return

	confs[key_map[key]] = value


class MyConfigParser(ConfigParser.ConfigParser):
	def __init__(self, defaults = None):
		ConfigParser.ConfigParser.__init__(self, defaults = None)
	def optionxform(self, optionstr):
		return optionstr


def process_file_node(node, parentDirN, confs):
	for key in node.attrib:
		if key != "name":
			set_confs(confs, key, node.attrib[key])

	scriptN = node.attrib["name"]
	confPaser = MyConfigParser()
	confPaser.read(modelScriptName)

	for key in confs:
		(section, option) = key.split(".")
		confPaser.set(section, option, confs[key])

	scriptPath = os.path.join(parentDirN, scriptN + scriptSuffix)
	with open(scriptPath, "w+") as f:
		confPaser.write(f)



def process_node(node, parentName, parentDirN, confs):
	if node.tag != "entry" and node.tag != "file":
		if os.path.exists(os.path.join(targetDirN, node.tag)):
			print(node.tag + " dir exists!")
			sys.exit(1)

	if node.tag != "file":
		name = node.tag
		if node.tag == "entry":
			name = node.attrib["value"]
		curDirN = os.path.join(parentDirN, name)
		os.makedirs(curDirN)

		for key in node.attrib:
			if key != "value":
				set_confs(confs, key, node.attrib[key])
			else:
				set_confs(confs, parentName, node.attrib[key])

		for child in node:
			process_node(child, node.tag, curDirN, confs.copy())

	else:
		process_file_node(node, parentDirN, confs)





def create_scripts(xmlFN, targetDirN):
	tree = ET.parse(xmlFN)
	root = tree.getroot()

	process_node(root, "", targetDirN, dict())


if __name__ == '__main__':
	usage = " "
	parser = OptionParser(usage)
	parser.add_option("-x", action = "store", dest = "xmlFN", help = "xml file name")
	parser.add_option("-d", action = "store", dest = "targetDirN", help = "target directory name")
	parser.add_option("-m", action = "store", dest = "modelScriptName", help = "model script name [default.ini]", default = "default.ini")

	options, args = parser.parse_args(sys.argv[1:])

	modelScriptName = options.modelScriptName
	xmlFN = options.xmlFN
	targetDirN = options.targetDirN

	if not os.path.exists(modelScriptName):
		print("default script file does not exist")
		parser.print_help()
		exit(1)

	if xmlFN == None or targetDirN == None:
		print("not set -x or -d")
		parser.print_help()
		exit(1)

	create_scripts(xmlFN, targetDirN)
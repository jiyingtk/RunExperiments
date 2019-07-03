import xml.etree.ElementTree as ET
import ConfigParser
import os
import re
import sys
from xml.dom import minidom
from optparse import OptionParser


resultN = ""

def process_result(fileN):
	with open(fileN, 'r') as f:
		tag = 0
		for line in f.readlines():
			if tag == 1:
				opsPat = r'([\d\.]+)'
				m = re.search(opsPat, line)
				if m:
					return m.group(1)

			if "Transaction throughput" in line:
				tag = 1

		return ""


def dir_name_filter(name):
	inx = name.find("--")
	if inx != -1:
		name = name[:inx]
	
	if "origin4bit" in name:
		name = "origin"
	elif "region4MB" in name:
		name = "extend"

	if name[0].isdigit():
		name = "_" + name


	return name.replace(" ", "_")

def process(curN, node):
	names = os.listdir(curN)
	for name in names:
		subPath = os.path.join(curN, name)
		if os.path.isdir(subPath):
			dname = dir_name_filter(name)
			subNode = ET.SubElement(node, dname)
			process(subPath, subNode)
		elif name == resultN:
			resultVal = process_result(subPath)
			node.text = resultVal


def main(dirN, saveN):
	if dirN[-1] == "/":
		dirN = dirN[:-1]
	name = dirN
	inx = dirN.rfind("/")
	if inx != -1:
		name = dirN[inx + 1:]
	if name[0].isdigit():
		name = "_" + name

	root = ET.Element(name)
	process(dirN, root)

	rawText = ET.tostring(root)
	# print(rawText)
	dom = minidom.parseString(rawText)
	with open(saveN, 'w') as f:
		dom.writexml(f, "", "\t", "\n", "utf-8")


if __name__ == '__main__':
	usage = " "
	parser = OptionParser(usage)
	parser.add_option("-n", action = "store", dest = "dirN", help = "results directory name")
	parser.add_option("-o", action = "store", dest = "saveN", help = "ouput file name (xml format)")
	parser.add_option("-f", action = "store", dest = "resultN", default = "result.txt", help = "default result file name [result.txt]")

	options, args = parser.parse_args(sys.argv[1:])

	dirN = options.dirN
	saveN = options.saveN
	resultN = options.resultN

	if dirN == None or saveN == None:
		print("not set -n or -o")
		parser.print_help()
		exit(1)

	main(dirN, saveN)
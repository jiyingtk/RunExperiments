import sys
import os


def clearFile(fileName):
	f = open(fileName, "r")
	contents = f.readlines()
	f.close()
	for i in range(len(contents)):
		if contents[i].startswith("hasRun"):
			contents[i] = "hasRun = false\n"
	f = open(fileName, "w")
	f.writelines(contents)
	f.close()


def clear(dirName):
	if not os.path.isdir(dirName):
		clearFile(dirName)
		return
	pathDirs = os.listdir(dirName)
	for pathDir in pathDirs:
		child = os.path.join(dirName, pathDir)
		clear(child)


if __name__ == '__main__':
	if len(sys.argv) < 2:
		print("error input")
		exit(1)
        for i in range(1,len(sys.argv)):
            clear(sys.argv[i])
        

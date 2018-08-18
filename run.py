import re
import os
import sys

class ConfEntry:
	def __init__(self):
		pass

	def loadFile(self, fileName):
	
	def exec(self):
		
		self.clean()

	def clean(self):
		pass

class ScriptManage:
	script_dir = "script"

	def __init__(self):
		#check script folder
		if not os.path.exists(self.script_dir):
			os.makedirs(self.script_dir)
		self.stateMap = dict()


	def run(self):
		os.list



if __name__ == '__main__':
	scriptManage = ScriptManage() 	
	scriptManage.run()

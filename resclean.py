#!/usr/bin/env python
# encoding: utf-8

"""
resman

Help manage unused resources in Xcode projects

Version 1.0

Created by Sumeru Chatterjee
"""

from optparse import OptionParser
import pdb
import sys
import os
from subprocess import call
from subprocess import Popen
from subprocess import PIPE
import shutil

def main():
	usage = '''%prog -p <Project Directory> -d <Resource Directory> -x <xcode-project> <options>

Resource Cleaner.
Helps Clean unused resources (png/jpg/gif/tiff) in Xcode projects.
The source files that are searched are (*.h,*.m,*.xib,*.nib)'''

	parser = OptionParser(usage = usage)
	parser.add_option("-x", "--xcode-project", dest="xcodeproject",
                    help="Search for resource usage from all source code files in this project",
                    action="append")
	parser.add_option("-p", "--projectdir", dest="project_dir",
                    help="Search for resource usage from source code files in in this directory", 
                    action="append")
	parser.add_option("-d", "--resourcedir", dest="resource_dir",
                    help="REQUIRED:Get the resources from this directory",
                    action="append")
	parser.add_option("-n", "--no-recursive", dest="norecurse",
                    help="Get the resources from the first subdirectory in RESOURCE_DIR only",
                    action="store_true")
	parser.add_option("-v", "--verbose", dest="verbose",
                    help="Display verbose output",
                    action="store_true")
	parser.add_option("-m","--move", dest ="move",
                    help="Move all invalid resources to invalid resources folder",
                    action="store_true")

	(options, args) = parser.parse_args()

	if not((options.__dict__["xcodeproject"]) or (options.__dict__["project_dir"])) or not((options.__dict__["xcodeproject"]) or (options.__dict__["resource_dir"])):
		parser.print_help()
		exit(0)

	xcodeproject = os.path.abspath(options.__dict__["xcodeproject"][0])
	resource_dir = os.path.abspath(options.__dict__["resource_dir"][0])
	project_dir = os.path.abspath(options.__dict__["project_dir"][0])
	verbose = options.__dict__['verbose']
	norecurse = options.__dict__['norecurse']
	move = options.__dict__['move']
		
	resourcelist = get_resource_files(resource_dir,norecurse)
	
	print "\nCalculating Sizes ..\n\n"	
	
	totalsize = 0
	sizedictionary = {}
	for file in resourcelist:
		sizedictionary[file] = os.path.getsize(file)
		totalsize += sizedictionary[file]
	
	
	if resourcelist:
		print "%(num)s resource files found in resource directory %(dir)s\n\n"%{'num':len(resourcelist),'dir':resource_dir}
		if verbose:
			print "Resource Files"
			print "-----------------\n"
			print "\n".join(os.path.basename(file)+" Size:"+convert_bytes(sizedictionary[file]) for file in resourcelist)
			print "\n\n"
	else:
		print "\n\nERROR:No resource files found in directory %(dir)s\n\n"%{'dir':resource_dir}
		exit(0)
				
			
	sourcelist = get_project_files_from_dir(project_dir)
	if sourcelist:
		print "%(num)s source or ib files found in project directory %(dir)s\n\n"%{'num':len(sourcelist),'dir':project_dir}
		if verbose:
			print "Source Files"
			print "-----------------\n"
			print "\n".join(os.path.basename(file) for file in sourcelist)
			print "\n\n"
	else:
		print "\n\nERROR:No source(*.h/*.m/) or ib files(*.xib/*.nib) found in directory %(dir)s..Aborting\n\n"%{'dir':project_dir}
		exit(0)
		
	print "Now Validating each resource file..\n\n"
	
	sourcelist_file = "./filelist.temp"
	outfile = open(sourcelist_file,"w")
	for sourcefile in sourcelist:
		escapedsourcefile = sourcefile.replace(" ","\ ")
		outfile.write(escapedsourcefile+"\n")
	
	outfile.close()
	invalid_resource_list = []
	invalidsize = 0


	for resource_file in resourcelist:
		valid = validate(resource_file,sourcelist_file,verbose)
		
		if not valid:
			print "Resource %(file)s Size:%(size)s - Invalid"%{'file':os.path.basename(resource_file),'size':convert_bytes(sizedictionary[resource_file])}
			invalid_resource_list.append(resource_file)
			invalidsize += os.path.getsize(resource_file)
		else:
			if verbose:
				"Resource %(file)s Size:%(size)s - Invalid"%{'file':os.path.basename(resource_file),'size':convert_bytes(sizedictionary[resource_file])}
	
	print "\n\nSummary\n--------------"
	print "Total Number of Resources :%d"%len(resourcelist)
	print "Total Size of Resources :%s"%convert_bytes(totalsize)
	print "Total Number of Invalid Resources :%d"%len(invalid_resource_list)
	print "Total Size of Invalid Resources :%s"%convert_bytes(invalidsize)
	os.remove(sourcelist_file)

	if move and invalid_resource_list:
		invalid_dir = resource_dir+"/"+"invalid"

		if not os.path.exists(invalid_dir):
			os.makedirs(invalid_dir)
			
		for resource_file in invalid_resource_list:
			src = resource_file
			dst = invalid_dir+"/"+os.path.basename(resource_file)
			shutil.move(src,dst)
	
	print "\n\n"

def validate(resource_file,sourcelist_file,verbose):
	if os.path.exists(resource_file):
		resourcefilename = os.path.basename(resource_file)
		filename = resourcefilename.split('.')[0]
		ext = "".join(resourcefilename.split('.')[1:])
		filename = filename.replace("@2x","")

		regex = "(<string.*?>|\"|\"bundle://)%(name)s(.%(ext)s)?(</string>|\")"%{'name':filename,'ext':ext}

		if verbose:
			print "\n\nValdating File:%(file)s,Search Regex:%(regex)s"%{'file':resourcefilename,'regex':regex}
						
		p1 = Popen(["cat","filelist.temp"],stdout=PIPE)	
		p2 = Popen(["xargs","egrep",regex],stdin=p1.stdout,stdout=PIPE)
		p1.stdout.close()
		grep_output = p2.communicate()[0]
		p1.wait()
		if not grep_output:
			return False
		else:
			if verbose:
								print "Matches :\n"+grep_output
			return True	
	else:
		print "\n\nERROR:Resource File %s does not exist..Aborting\n\n"%resource_file
		exit(0)	
		

def get_resource_files(resource_dir,norecurse=False):
	
	filelist = []
	if os.path.exists(resource_dir):
		if not norecurse:
						p1 = Popen(["find","-E",resource_dir,"-type","f","-regex","(.*png|.*jpg|.*gif|.*tiff)"], stdout=PIPE)
		else:
						p1 = Popen(["find","-E",resource_dir,"-type","f","-regex","(.*png|.*jpg|.*gif|.*tiff)","-maxdepth","1"], stdout=PIPE)
			
		for file in p1.stdout:
						if not "DS_Store" in file:
								filelist.append(file[:-1])
		
		p1.stdout.close()
		return filelist
	else:
		print "\n\nERROR:Directory %s does not exist..Aborting\n\n"%resource_dir
		exit(0)	


def get_project_files_from_dir(project_dir):
	
	filelist = []
	if os.path.exists(project_dir):
		p1 = Popen(["find","-E",project_dir,"-type","f","-regex","(.*h|.*m|.*xib|.*nib)"], stdout=PIPE)
			
		for file in p1.stdout:
			filelist.append(file[:-1])
		
		p1.stdout.close()
		return filelist
	else:
		print "\n\nERROR:Directory %s does not exist..Aborting\n\n"%project_dir
		exit(0)		

def convert_bytes(bytes):
	bytes = float(bytes)
	if bytes >= 1099511627776:
		terabytes = bytes / 1099511627776
		size = '%.2fT' % terabytes
	elif bytes >= 1073741824:
		gigabytes = bytes / 1073741824
		size = '%.2fG' % gigabytes
	elif bytes >= 1048576:
		megabytes = bytes / 1048576
		size = '%.2fM' % megabytes
	elif bytes >= 1024:
		kilobytes = bytes / 1024
		size = '%.2fK' % kilobytes
	else:
		size = '%.2fb' % bytes
	return size

if __name__ == "__main__":
	sys.exit(main())
#!/usr/bin/python
# TREB wordpress listing import script
# www.stardothosting.com : Managed Hosting Services
# www.shift8web.com : Web Design and Development

#Copyright (C) 2013 Star Dot Hosting Inc

#This program is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.

#This program is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with this program in the LICENSE file.  If not, see <http://www.gnu.org/licenses/>


import csv, sys, urllib, urlparse, string, time, locale, os, os.path, socket, re, requests, xmlrpclib,errno
import ConfigParser
import math
import MySQLdb
from datetime import date, timedelta
from ftplib import FTP
from pygeocoder import Geocoder
from tempfile import mkstemp
from shutil import move
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.taxonomies import *
from wordpress_xmlrpc.methods.posts import *
from wordpress_xmlrpc.methods.users import *
from wordpress_xmlrpc.methods import *

#twitter

# debug
import pprint 

# Read configuration file parameters
Config = ConfigParser.ConfigParser()
Config.read(os.path.expanduser('~/.treb_wordpress'))

# Check command arguments
if len(sys.argv) <= 1 :
	print "\nUsage Syntax :"
        print "\ntreb_fetch.py [option1] [option2]"
        print "Option 1 : \"avail\" \"unavail\" , processes available or unavailable listings"
        print "Option 2 : Number of days prior to gather listing data"
        sys.exit(0)

###################
# Functions START #
###################

def ConfigSectionMap(section):
    dict1 = {}
    options = Config.options(section)
    for option in options:
        try:
            dict1[option] = Config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

def ftpget( hostname, localpath, remotepath, filename ) :

        # Go to destination DIR
        os.chdir(localpath)

        # FTP Details
        ftp = FTP(hostname)
        ftp.login(user + "@photos", password)

        ftp.cwd(remotepath)
        ftp.sendcmd("TYPE i")
        f = open(filename,"wb")
        try:
                ftp.retrbinary("RETR " + filename,f.write)
        except:
                print "File not found.. exiting .."
                os.remove(filename)
        try:
                ftp.close()
        except:
                print "Error closing FTP connection ..."

#Searches wordpress posts based on title
#def find_id(title):
# DELETED BY DAVID

#Searches wordpress post content for MLS number (or anything else)
# DELETED BY DAVID
# 

#Take text and replace words that match an array
def replace_words(text, word_dic):
	rc = re.compile('|'.join(map(re.escape, word_dic)))
	def translate(match):
		return word_dic[match.group(0)]
	return rc.sub(translate, text)

#Silent way of removing a file if it already exists
def silentremove(file_name):
    try:
        os.remove(file_name)
    except OSError, e: # this would be "except OSError as e:" in python 3.x
        if e.errno != errno.ENOENT: # errno.ENOENT = no such file or directory
            raise # re-raise exception if a different error occured

#Filter out agents from exclude list
def ex_agent(aid, exlist):
    exlist_in = exlist.split(',')
    for excludeagent in exlist_in:
         if str(aid) == str(excludeagent):
             return(excludeagent)
    return(False)

#Filter out agent ids from include or agent match
def is_agent(aid, inlist):
    inlist_in = inlist.split(',')
    for includeagent in inlist_in:
         if str(aid) == str(includeagent):
             return(includeagent)
    return(False)


#################
# Functions END #
#################

# Get Connection and Authentication  config data
wp_url = ConfigSectionMap("wordpress")['wp_url']
wp_username = ConfigSectionMap("wordpress")['wp_username']
wp_password = ConfigSectionMap("wordpress")['wp_password']
user = ConfigSectionMap("treb")['trebuser']
password = ConfigSectionMap("treb")['trebpass']
agent_id = ConfigSectionMap("treb")['agent_id']
min_listing = Config.getint('treb', 'minimum_listing')
int_date = int(sys.argv[2])
avail_opt = sys.argv[1]
rootdir = ConfigSectionMap("treb")['root_dir']
userperm = Config.getint('wordpress', 'user_perm')
groupperm = Config.getint('wordpress', 'group_perm')
exclude_agent = ConfigSectionMap("treb")['agent_exclude']
outfile = ConfigSectionMap("treb")['output_file']
cur_path = os.getcwd()
phonemsg = ConfigSectionMap("treb")['phone_msg']
tw_enabled = ConfigSectionMap("twitter")['enabled']
if tw_enabled == "true":
    tw_consumer = ConfigSectionMap("twitter")['consumer']
    tw_secret = ConfigSectionMap("twitter")['secret']
    tw_token = ConfigSectionMap("twitter")['access_token']
    tw_token_secret = ConfigSectionMap("twitter")['access_token_secret']
    tw_hashtags = ConfigSectionMap("twitter")['hashtags']
    tw_bitlyuser = ConfigSectionMap("twitter")['bitly_user']
    tw_bitlykey = ConfigSectionMap("twitter")['bitly_key']

# Get blog URL
#wp_site = Client(wp_url, wp_username, wp_password)
#siteurl = wp_site.call(options.GetOptions(['home_url']))[0].value


# declare variables based on arguments
past_date = date.today() - timedelta(int_date)
the_day = past_date.strftime('%d')
the_mon = past_date.strftime('%m')
the_yr = past_date.strftime('%-Y')
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
	
# check if slash was added to rootdir
if rootdir.endswith('/'):
	print "Slash detected in rootdir .."
else:
	rootdir = rootdir + "/"

# build the url query string
url = "http://3pv.torontomls.net/data3pv/DownLoad3PVAction.asp?user_code=" + user + "&password=" + password + "&sel_fields=*&dlDay=" + the_day + "&dlMonth=" + the_mon + "&dlYear=" + the_yr + "&order_by=&au_both=" + avail_opt + "&dl_type=file&incl_names=yes&use_table=MLS&send_done=no&submit1=Submit&query_str=lud%3E%3D%27" + the_yr + the_mon + the_day + "%27"

print url
#sys.exit()

# retrieve URL and  write results to filename
silentremove(outfile)
urllib.urlretrieve(url,outfile)


# Available or Unavailable Listing Logic
if avail_opt == "avail":

	# read the csv file
	f = open(outfile, 'r') #open file
	try:
    		r = csv.reader(f) #init csv reader
    		r.next()
    		for row in r:
        		description = row[2]
        		streetname = row[273]
        		streetnumber = row[275]
			streetsuffix = row[276]
			address = row[3]
        		postalcode = row[330]
        		bathrooms = row[10]
        		bedrooms = row[15]
        		bedplus = row[16]
        		houseclass = row[29]
        		extras = row[69]
        		listagent = row[111]
        		listprice = row[120]
        		mlsnumber = row[130]
        		squarefoot = row[269]
        		virtualtour = row[292]
        		pictures = row[174]
        		inputdate = row[174]
        		lastupdate = row[123]
        		solddate = row[24]
        		agentid = row[333]

			#Sanitize Variables
			listpricefix = locale.currency(int(listprice), grouping=True )
			#description = description.replace(":", "\:").replace("/", "\/").replace("&", "\&")
			#virtualtour = virtualtour.replace(":", "\:").replace("/", "\/").replace("&", "\&")


		# Set category and verify if other agent listing is over minimum_listing in config file
                        #include = is_agent(agentid, agent_id)
			#if agentid == agent_id:

 	       		# Get the latitude + longitude variables

        		# Set variable for virtual tour

			# Start prepping the uploads folder for the MLS listing images
			if pictures == "Y":
				mlsimage = mlsnumber[-3:]
				print "MLS Image : " + mlsimage

				# Create upload folder if it doesnt exist
				if not os.path.exists(rootdir + '/wp-content/uploads/treb/' + mlsnumber):
    					os.makedirs(rootdir + '/wp-content/uploads/treb/' + mlsnumber)

				# GET The image files via FTP
				#print "Starting FTP connection to get listing photos .."
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/1/" + mlsimage, mlsnumber + ".jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/2/" + mlsimage, mlsnumber + "_2.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/3/" + mlsimage, mlsnumber + "_3.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/4/" + mlsimage, mlsnumber + "_4.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/5/" + mlsimage, mlsnumber + "_5.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/6/" + mlsimage, mlsnumber + "_6.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/7/" + mlsimage, mlsnumber + "_7.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/8/" + mlsimage, mlsnumber + "_8.jpg")
				ftpget( "3pv.torontomls.net", rootdir + "/wp-content/uploads/treb/" + mlsnumber, "mlsmultiphotos/9/" + mlsimage, mlsnumber + "_9.jpg")
				print "FTP Download complete .."
		
				# Adjust permissions , change 33 to whatever GID/UID you need
				#os.chown(rootdir + "/wp-content/uploads/treb/" + mlsnumber, userperm, groupperm)
				#for root, dirs, files in os.walk(rootdir + "/wp-content/uploads/treb/" + mlsnumber):
				#	for filename in files:
				#		os.chown(os.path.join(root, filename), userperm, groupperm)
        		else:
                		print "No photos ..."

        		# Generate post content from the template file

			#Replacements from the template

			# Prepare the post
	
			# Check if post exists already
			#post_id = find_id(post.title)
                                # GET The image files via FTP

                                # Adjust permissions , change 33 to whatever GID/UID you need
                                os.chown(rootdir + "/wp-content/uploads/treb/" + mlsnumber, userperm, groupperm)
                                for root, dirs, files in os.walk(rootdir + "/wp-content/uploads/treb/" + mlsnumber):
                                        for filename in files:
                                                os.chown(os.path.join(root, filename), userperm, groupperm)
				#Output text to a post file to be eventually posted to wordpress	
	finally:
		f.close() #cleanup
		silentremove(outfile)
	
	# Unavailable option
elif avail_opt == "unavail" :

        # read the csv file
        f = open(outfile, 'r') #open file
        try:
                r = csv.reader(f) #init csv reader
                r.next()
                for row in r:
                        mlsnumber = row[1]
		
		# Prepare post title for search
		wp = Client(wp_url, wp_username, wp_password)
		unavail_id = unlist_mls(mlsnumber)
		if unavail_id : 
			print "The following post has been unpublished : " + mlsnumber 
		else :
			print "No matches for any posts with the MLS " + mlsnumber

	finally:
		f.close() #cleanup
#		silentremove(outfile)

else :
	print "Invalid command options given"
	sys.exit(0)

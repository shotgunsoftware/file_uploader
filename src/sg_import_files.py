#!/usr/bin/env python
'''
Copyright (c) 2011, Shotgun Software Inc
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 - Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer. 
   
 - Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
   
 - Neither the name of the Shotgun Software Inc nor the names of its
   contributors may be used to endorse or promote products derived from this
   software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
# ------------------------------------------------------------------------------
# Imports
# ------------------------------------------------------------------------------
import shotgun_api3
from pprint import pprint
import re
import os

__VERSION__ = 1.0

# ------------------------------------------------------------------------------
# TODO
# ------------------------------------------------------------------------------
# - use logging instead of print statements
# - make interactive prompt


# ------------------------------------------------------------------------------
# User-Defined Variables
# ------------------------------------------------------------------------------
# Shotgun server info
server_path = "" # https://your.shotgunstudio.com
script_name = "" # add your script name here     
script_key = "" # add your application key here

# set whether uploading a file or setting the thumbnail 
# valid options are 'thumbnail', 'file'
mode = 'thumbnail'

# root path to start searching for files
root_path = '/path/to/your/files/'

# regex pattern to match for valid files. Note the () are required to capture 
# the section that is the entity code we'll be looking up to pair the file with.
# eg.
pattern = re.compile('(r\d{2}_sn\d{4})_v\d{3}.jpg')
#pattern = '(.*).mov$'

# type of entity to link the file to
entity_type = 'Shot'

# (Optional) internal field name to store uploaded file in for the entity.
# This isn't needed for thumbnails. If you don't want to specify this, set it 
# to None
file_field = None


# ------------------------------------------------------------------------------
# Main 
# ------------------------------------------------------------------------------
if __name__ == '__main__':    

    # --------------------
    # validations
    # --------------------
    if not script_name or not script_key or not server_path:
        print "="*20
        print "ERROR: you must define your 'server_path', 'script_name', "\
              "and 'script_key'"
        print "="*20
        exit(1)
        
    if mode not in ['file','thumbnail']:
        print "="*20
        print "ERROR: mode must be 'file' or 'thumbnail'. Current value is "\
              "'%s'" % mode
        print "="*20
        exit(1)
    
    if not os.path.exists(root_path):
        print "="*20
        print "ERROR: root_path '%s' doesn't exist or isn't readable" % root_path
        print "="*20
        exit(1)
    
    sg = shotgun_api3.Shotgun(server_path, script_name, script_key)
    print "\nConnected to Shotgun at %s" % server_path

    if entity_type not in sg.schema_entity_read().keys():
        print "="*20
        print "ERROR: entity_type '%s' is not a valid Shotgun entity type" % \
              (entity_type)
        print "="*20
        exit(1)
    
    if file_field:
        try:
            sg.schema_field_read(entity_type, file_field)
        except shotgun_api3.Fault, e:
            print "="*20
            print "ERROR: file_field '%s' does not exist for entity type '%s'" % \
                  (file_field, entity_type)
            print "="*20
            exit(1)
    
    print "Starting import from %s" % root_path
    print "Filtering for files that match pattern: %s" % pattern
    pattern = re.compile(pattern)
    # --------------------
    # end validations
    # --------------------
    
    
    """
    Start at the root_path and traverse the files and directories looking for 
    files that match the regex (pattern). Try and find the entity in Shotgun 
    who's code matches entity_name. If a single entity is found, upload the 
    file.

    If file_field is set, link the uploaded file to that field. 

    If more than one entity is found matching entity_name, issue a warning and 
    skip it. If no entity is found matching entity_name, issue a warning.

    This assumes that the entity code is contained within the filename. If the 
    entity code is contained within the full path, the following logic won't 
    work but can be updated easily to construct the entity name by modifying the
    m = pattern.search(filename) line to search on the file_path instead with a 
    different regex.
    """
    for root, dirs, files in os.walk(root_path):
        for filename in filter(pattern.search, files):
            file_path = os.path.join(root, filename)               
            # find the entity name defined by the pattern within the file_path 
            m = pattern.search(filename)
            # should never hit this since we already did a regex on the filenames
            if len (m.groups()) == 0:
                print "WARNING: no %s matching pattern found (%s)" % \
                (entity_type, file_path)
            else:
                # look up the entity matching the entity name matched in the 
                # filename
                entity_name = m.groups(1)[0]
                entity = sg.find(entity_type, [['code', 'is', entity_name]])
                if len(entity) > 1:
                    print "WARNING: Found more than one %s named '%s' ... "\
                          "skipping (%s)" % (entity_type, entity_name, file_path) 
                elif len(entity) < 1:
                    print "WARNING: %s '%s' not found (%s)" % (entity_type, 
                                                               entity_name, 
                                                               file_path) 
                else:
                    if mode == 'thumbnail':
                        if sg.upload_thumbnail(entity_type, entity[0]['id'], 
                                               file_path):
                            print "uploaded thumbnail for %s '%s' (%s) " % \
                                  (entity_type, entity_name, file_path)       
                    
                    elif mode == 'file':
                        if sg.upload(entity_type, entity[0]['id'], file_path, 
                                     file_field):
                            print "uploaded file for %s '%s' (%s) " % \
                                  (entity_type, entity_name, file_path)       
                        
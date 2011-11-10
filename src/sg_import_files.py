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
import logging
import logging.handlers
import re
import os
import optparse

__version__ = '1.1'
__status__ = 'Stable'

# ------------------------------------------------------------------------------
# USER-DEFINED VARIABLES
# ------------------------------------------------------------------------------
# --- Shotgun server info --- #
server_path = ""
script_name = ""
script_key = ""
# --- Regex pattern --- #
# regex pattern to match for valid files. Note the () are required to capture
# the section that is the entity code we'll be looking up to pair the file with.
match_pattern = '^(.+(?:_V\d+))_.*.mov$'
# --- Default mode --- #
# choices are 'file' and 'thumbnail'
default_mode = 'file'
# --- Default entity type --- #
# entity type to upload the file to
default_entity_type = 'Version'
# --- Default field name --- #
# field name to store the file in on entity type (ignored if we're in thumbnail
# mode)
default_field_name = 'sg_qt'
# --- experimental --- #
use_colors = False
# --- END USER-DEFINED VARIABLES --- #


# --- LOGGING --- #
LOG = logging.getLogger("sg_import_files")
LOG.setLevel(logging.DEBUG)
# create console handler and set level to info
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
simple_format = logging.Formatter('%(message)s')
ch.setFormatter(simple_format)
LOG.addHandler(ch)
#file handler for more info
fh = logging.handlers.RotatingFileHandler(__file__+".log", maxBytes=5242880, backupCount=2)
fh.setLevel(logging.DEBUG)
dated_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(dated_format)
LOG.addHandler(fh)


# --- COLORS (for pretty output) --- #
class Colors(object):
    def __init__(self, enable=False):
        if enable:
            self.GRAY = '\033[37m'
            self.OKBLUE = '\033[34m'
            self.OKGREEN = '\033[92m'
            self.RED = '\033[31m'
            self.BOLD = '\033[1m'
            self.UNBOLD = '\033[0m'
            self.ENDC = '\033[0m'

    def __getattr__(obj, v):
        return ''
bcolors = Colors(use_colors)


# ----- ERRORS ----- #
def do_error(message, filename=None):
    """Something went wrong severe enough to bail out of the script. Log the
    error message and exit.
    """
    err = ""
    if filename:
        err += "[%s] " % filename,
    err += "%sERROR%s: %s" % (bcolors.RED, bcolors.ENDC, message)
    LOG.error(err)
    exit(1)


def do_notok(filename, message):
    """Mark current filename being processed as failed and log the message.
    """
    msg = "[%sFAILED%s]" % (bcolors.RED, bcolors.ENDC)
    # print msg
    LOG.debug("%s %s: %s" % (filename, msg, message))
    LOG.warning("%s %s" % (filename, msg))
    error_files.append({'file':filename,'reason':message})


def do_ok(filename):
    """Mark current filename being processed as successful and log the message.
    """
    msg = "[%sOK%s]" % (bcolors.OKGREEN, bcolors.ENDC)
    LOG.info("%s: %s" % (filename, msg))
    ok_files.append(filename)


def parse_options():
    """Parse command-line options to set the variables for the script. If any
    are missing, user will be prompted for them with suggestions from the
    defaults provided in the user-defined variables section of this script.
    """
    usage = "USAGE: %prog [options]\nTry %prog --help for more information"
    version_string = "v%s (%s)" % (__version__, __status__)
    full_version_string = "%prog " + version_string
    description = "%prog provides a simple way to mass-upload thumbnails and " \
        "files and link them to entities based on a regex pattern.\n\n" + full_version_string
    parser = optparse.OptionParser(usage=usage, version=full_version_string, description=description)
    parser.add_option("-d", "--directory", type="string", dest="root_path", default=None, help="root directory to search for matching files")
    parser.add_option("-m", "--mode", type="string", dest="mode", default=default_mode, help="Mode to upload files as, either 'file' (default) or 'thumbnail'")
    parser.add_option("-e", "--entity_type", type="string", dest="entity_type", default=None, help="entity type to upload files to (ie. Shot, Version, Asset")
    parser.add_option("-f", "--field_name", type="string", dest="field_name", default=None, help="(optional) name of the field on <entity_type> to store the file in. Not used in thumbnail mode.")

    return parser


def do_validate():
    """Validate that the values provided to the script are okay. Validates
    Shotgun connection succeeds, entity type and field name exists, mode is
    valid, and the directory provided exists.
    """
    # ----- Validations ----- #
    if not script_name or not script_key or not server_path:
        do_error("you must define your 'server_path', 'script_name',and 'script_key'")

    sg = shotgun_api3.Shotgun(server_path, script_name, script_key)
    LOG.debug("Connected to Shotgun at [%s%s%s]" % (bcolors.BOLD, server_path, bcolors.UNBOLD))

    if options.entity_type not in sg.schema_entity_read().keys():
        do_error("entity_type '%s' is not a valid Shotgun entity type" % options.entity_type)

    if options.field_name:
        try:
            sg.schema_field_read(options.entity_type, options.field_name)
        except shotgun_api3.Fault, e:
            do_error("field name '%s' does not exist for entity type '%s'" % (options.field_name, options.entity_type))

    if options.mode not in ['file','thumbnail']:
        do_error("mode must be 'file' or 'thumbnail'. Current value is '%s'" % mode)

    if not os.path.exists(options.root_path):
        do_error("the directory '%s' doesn't exist or isn't readable" % options.root_path)


    LOG.debug("Starting import from [%s%s%s]" % (bcolors.BOLD, options.root_path, bcolors.UNBOLD))
    LOG.debug("Filtering for files that match pattern: [%s%s%s]\n" % (bcolors.BOLD, match_pattern, bcolors.UNBOLD))
    return sg
    # ----- end Validations ----- #


def pass_custom_regexes(entity_name):
    """Perform any additional validation voodoo here for valid entity names.
    """
    # ensure that version is in the filename
    if "_v" not in entity_name and "_V" not in entity_name:
        do_notok(filename, 'Missing version portion of filename (ie. _v1)')
        return False
    return True


def get_entity(filename, m):
    """Parse entity name from filename pattern match and lookup entity in Shotgun
    based matching that name. The file will fail if multiple entities are found
    or no entity is found. Will also fail if the pass_custom_regexes() function
    fails.
    """
    entity_name = m.groups(1)[0]
    entity_type = options.entity_type
    if not pass_custom_regexes(entity_name):
        return False

    entity = sg.find(entity_type, [['code', 'is', entity_name]], ['code'])
    if len(entity) > 1:
        do_notok(filename,'Found more than one %s named "%s"' % (options.entity_type, entity_name) )
        return False
    elif len(entity) < 1:
        do_notok(filename,'%s named "%s" not found' % (options.entity_type, entity_name) )
        return False
    else:
        return entity[0]


def check_attachment_exists(entity_type, entity_id):
    """For file mode only, if uploading files to a specific field, checks to see
    if there is already a file in that entity field. File upload will fail if
    a file already exists on the entity so we don't accidentally blow things
    away. You can disable this if you like.
    """
    # not applicable if we're not uploading to a field
    if not options.field_name:
        return False
    result = sg.find_one(entity_type, [['id', 'is', entity_id]], [options.field_name])
    if result[options.field_name]:
        LOG.debug( 'File already exists for %s %s in field %s: %s' % (entity_type, entity_id, options.field_name, result[options.field_name]))
        return True
    return False


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------
if __name__ == '__main__':
    """Main program execution. Parse options from command line and ask the user
    to provide any missing variables. Validate the input and then attempt to parse
    the entity name from the filename according to the regex_pattern defined in
    the user-defined variables section of this script. If a match is found, look
    up the entity in Shotgun. If a single entity is found in Shotgun, attempt
    to upload the file to the entity.
    """
    parser = parse_options()
    (options, args) = parser.parse_args()
    while not options.root_path:
        user_path = raw_input("What is the full path to the directory to import? ")
        options.root_path = user_path.strip()

    while not options.entity_type:
        options.entity_type = raw_input("What entity type are you importing to? [%s] " % default_entity_type)
        if not options.entity_type:
            options.entity_type = default_entity_type

    if options.mode != 'thumbnail':
        while not options.field_name:
            options.field_name = raw_input("What field on %s do you want to store the file in? (or 'none') [%s] " % (options.entity_type, default_field_name))
            if not options.field_name:
                options.field_name = default_field_name
        if options.field_name == 'none':
            options.field_name = None

    # validate settings and input are okay and we're good to go
    sg = do_validate()
    LOG.info(' ')
    """
    Start at the root_path and traverse the files and directories looking for
    files that match the regex (pattern). Try and find the entity in Shotgun
    who's code matches entity_name. If a single entity is found, upload the
    file.

    If options.field_name is set, link the uploaded file to that field.

    If more than one entity is found matching entity_name, issue a warning and
    skip it. If no entity is found matching entity_name, issue a warning.

    This assumes that the entity code is contained within the filename. If the
    entity code is contained within the full path, the following logic won't
    work but can be updated easily to construct the entity name by modifying the
    m = pattern.search(filename) line to search on the file_path instead with a
    different regex.
    """
    pattern = re.compile(match_pattern)
    ok_files = []
    error_files = []
    for root, dirs, files in os.walk(options.root_path):
        LOG.info("[%s]" % root)
        for filename in files:
            LOG.debug(" processing %s..." % (filename),)
            file_path = os.path.join(root, filename)
            # find the entity name defined by the pattern within the file_path
            m = pattern.search(filename)
            if not m or len(m.groups()) == 0:
                do_notok(filename, "Filename doesn't match expected regex pattern: %s" % match_pattern)
            else:
                entity = get_entity(filename, m)
                if not entity:
                    continue
                if options.mode == 'thumbnail':
                    if sg.upload_thumbnail(entity['type'], entity['id'],
                                           file_path):
                        do_ok(filename)
                        LOG.debug( "uploaded thumbnail for %s '%s' (%s) " % \
                              (options.entity_type, entity['code'], file_path) )
                elif options.mode == 'file':
                    attachment_exists = check_attachment_exists(entity['type'], entity['id'])
                    if not attachment_exists:
                        if sg.upload(entity['type'], entity['id'], file_path,
                                     options.field_name):
                            do_ok(filename)
                            LOG.debug("Uploaded file %s to %s '%s'" % (file_path, options.entity_type, entity['code'] ))
                    else:
                        do_notok(filename, "File already exists on %s '%s' in field %s. Skipping." % (options.entity_type, entity['code'], options.field_name))

        # --- Summarize what happened --- #
        LOG.info( " " )
        LOG.info("-"*80)
        LOG.info(" SUMMARY: %s " % options.root_path)
        LOG.info("-"*80)
        LOG.info(" The following files were uploaded successfully:")
        LOG.info( " " )
        if len(ok_files) == 0:
            LOG.info("     None")
        else:
            for f in ok_files:
                LOG.info("     %s%s%s" % (bcolors.OKGREEN, f, bcolors.ENDC))

        if len(error_files) > 0:
            LOG.info( " " )
            LOG.info( " The following files had errors and were not uploaded:" )
            LOG.info( " " )
            for f in error_files:
                LOG.info( "     %s%s%s: %s" % (bcolors.RED, f['file'], bcolors.ENDC, f['reason']) )





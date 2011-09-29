Introduction
============
This is a simple script for uploading multiple files or thumbnails to Shotgun and linking them with the correct entities. It requires that the full path to the file contains enough identifying information to identify the entity it belongs to. Some studios may be able to use this with little modification, especially if the filenames match the entity names. However, it's relatively simple to adjust the settings and code to fit your specific needs.

#Configuration
In order to get the script running, you will need to provide the following:

###Connection Info

- **Shotgun URL**  
`server_path = 'https://mystudio.shotgunstudio.com'`  
- **Script Name**  
`script_name = 'file_importer'`  
- **Application Key**  
`script_key = '0123456789abcdef0123456789abcdef01234567'`  

###File Info

- **Root path to your files**  
`root_path = '/path/to/movies'`  
- **Regex pattern to match identifying information for the entity to link to**  
`pattern = '(.*).mov$'`  
(this pattern assumes that each movie is named with the same name as the entity and ends in '.mov')

###Shotgun Info

- **Mode to run in**  
`mode = 'file'` 
(valid options are 'thumbnail' or 'file')  
- **Entity type to upload the files to**  
`entity_type = 'Version'`  
- **Optional field name of a File/Link field to store the file in**  
`file_field = 'sg_uploaded_movie'`

#Running The Script
When you run the script, it will start at the `root_path` and traverse the files and directories looking for files that match the regex (`pattern`). It will then try and find the entity in Shotgun with a code that matches the `entity_name` (identified in the regex). If a single entity is found, it will upload the file.

If `file_field` is set, it will link the uploaded file to that field. 

If more than one entity is found matching `entity_name`, it will issue a warning and skip it. If no entity is found matching `entity_name`, it will issue a warning.

By default, the script assumes that the entity code is contained within the filename. If the entity code is contained within the full path, the default logic won't work but can be updated easily to construct the entity name by modifying the `m = pattern.search(filename)` line to search on the `file_path` instead with a different regex.
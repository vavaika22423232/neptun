import os, sys
os.environ['PARSER_TEST']='1'
print('BEFORE IMPORT APP')
import app
print('AFTER IMPORT APP, has process_message =', hasattr(app,'process_message'))
print('MODULE NAMES LOADED =', len(sys.modules))

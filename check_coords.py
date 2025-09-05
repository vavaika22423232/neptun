import os
os.environ['PARSER_TEST']='1'
import app
print({k: app.CITY_COORDS.get(k) for k in ['херсон','нікополь','марганець','дружківка','ворожба']})

# -*- coding: utf-8 -*-
from odoo import fields, models
from functools import partial
#import geocoder
#from geopy.geocoders import Nominatim
#from geopy import geocoders
#from geopy.exc import GeocoderTimedOut
from geopy.geocoders import Nominatim
from geopy.geocoders import GoogleV3




class LatitudeLength(models.Model):
	_name = 'latitude.length'
	_description = 'Postal code and colonies'

	name = fields.Char("Descripción", required=True)
	zipcode = fields.Char("Codigo postal", required=True)
	latitude = fields.Char(string="Latitud")
	length = fields.Char(string="Longitud")


	def action_generate_latitude_length(self):
		registros = self.env['latitude.length'].search([], order='zipcode desc')
		contador = 0
		contador2 = 0
		codigo_postal = ""
		for registro in registros:
			print ("Esto es el codigo_postal",codigo_postal)
			#if contador > 90:
			#	continue
			if codigo_postal == registro.zipcode:
				if result:
					registro.latitude = result.latitude
					registro.length = result.longitude
				else:
					registro.latitude= "pendiente"
					registro.length = "pendiente"
				contador2 = contador2 + 1
				print ("Esto es contador2",contador2)
			else:
				#geolocator = Nominatim(user_agent="Luigi's mapping app", timeout=2)
				#location_2 = geolocator.geocode("Quetzal 100, Leyes de reforma 1 secc")
				#print ("Esto es location_2 [longitud,latitud]",location_2)
				#geocode = partial(geolocator.geocode, language="es")
				#print(geocode("Quetzal 100, Leyes de reforma 1 secc"))
				geolocator = Nominatim(user_agent="Test")
				#print ("Esto es el codigo postal",registro.zipcode)
				result = geolocator.geocode(str(self.name)+" "+str(registro.zipcode))
				if result:
					registro.latitude = result.latitude
					registro.length = result.longitude
				else:
					registro.latitude= "pendiente"
					registro.length = "pendiente"
				codigo_postal = registro.zipcode
				contador = contador + 1 
				print ("Contador",contador)


			#geolocator = GoogleV3()
			#address, (latitude, longitude) = geolocator.geocode('México,'+str(registro.zipcode))
			#print (address, latitude, longitude)

			#geolocator = GeocoderDotUS(format_string="%s, Cleveland OH")
			#address, (latitude, longitude) = geolocator.geocode('México,'+str(registro.zipcode))
			#print (address, latitude, longitude)
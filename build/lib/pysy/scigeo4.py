# coding: utf-8
# Date: 2018-12-24 15:23
from osgeo import gdal, osr, ogr
import os, warnings
import numpy as np
try:
	import rasterio
except ImportError:
	print("No module named rasterio, using original gdal instead")

try:
	import geopandas
except ImportError:
	print("No module named geopandas, using original ogr/osr instead")

try:
	from pyproj import Proj, Geod, transform
except ImportError:
	Proj, Geod, transform = None, None, None
	print("No module named pyproj")


class Raster(object):
	"""docstring for Raster"""
	def __init__(self, raster_path):
		super(Raster, self).__init__()
		gdal.SetConfigOption('GDAL_FILENAME_IS_UTF8', 'NO')
		gdal.SetConfigOption('SHAPE_ENCODING', 'gb2312')
		try:
			self.path = raster_path.as_posix()
		except Exception as identifier:
			self.path = raster_path
		
	def __del__(self):
		pass

	def read(self):
		try:
			dataset = self.gdal_read()
		except Exception as identifier:
			dataset = self.rio_read()
		finally:
			return dataset

	def gdal_read(self):
		src = gdal.Open(self.path)
		cols = src.RasterXSize
		rows = src.RasterYSize
		bands = src.RasterCount
		proj = src.GetProjection()
		gt = src.GetGeoTransform()
		if bands == 1:
			array = src.ReadAsArray(0, 0, cols, rows)
		else:
			try:
				array = src.GetVirtualMemArray()
			except Exception as identifier:
				array = []
				for band in np.arange(bands) + 1:
					band_raster = src.GetRasterBand(band)
					data = band_raster.ReadAsArray(0, 0, cols, rows)
					array.append(data)
				array = np.array(array)
		return {"data": array, "info": {"gt": gt, "proj": proj, "count": bands}}

	def gdal_read_info(self):
		src = gdal.Open(self.path)
		files = src.GetFileList()
		meta = src.GetMetadata_List()
		sds = src.GetSubDatasets()
		cols = src.RasterXSize
		rows = src.RasterYSize
		bands = src.RasterCount
		gt = src.GetGeoTransform()
		proj = src.GetProjection()
		return {"FileLists": files, "metadata": meta, "subdatasets": sds,
				"shape": [rows, cols, bands], "gt": gt, "proj": [proj]}

	def gdal_readAll(self):
		data = self.gdal_read()["data"]
		info = self.gdal_read_info()
		return {"data": data, "info": info}

	def rio_read(self):
		warnings.filterwarnings("ignore")
		with rasterio.open(self.path) as src:
			array = src.read()
			profile = src.profile
		return {"data": array, "info": profile}

	def rio_readAll(self):
		"""
		c, a, b, f, d, e = src.transform
		gt = rasterio.transform.Affine.from_gdal(c, a, b, f, d, e)
		proj = src.crs
		count = src.count
		name = src.name
		mode = src.mode
		closed = src.closed
		width = src.width
		height = src.height
		bounds = src.bounds
		idtypes = {i: dtype for i, dtype in zip(
			src.indexes, src.dtypes)}
		meta = src.meta
		src = src.affine
		"""
		src = rasterio.open(self.path)
		return src

	def write(self, dataset, fulloutpath, gt = "OMIGLOBAL025", EPSGPROJCODE = 4326, datatype=gdal.GDT_Float32, dtype=rasterio.float64):
		try:
			self.gdal_write(dataset["data"], fulloutpath,
				gt = gt, EPSGPROJCODE = EPSGPROJCODE)
		except Exception as identifier:
			print(identifier)
			self.rio_write(dataset["data"],
				fulloutpath, dataset["info"], dtype)

	def gdal_write(self, array, fulloutpath, gt = "OMIGLOBAL025", EPSGPROJCODE = 4326, datatype=gdal.GDT_Float32):
		"""
		parameter: array, fulloutpath, gt = "OMIGLOBAL025", datatype = gdal.GDT_Float32
		return: NONE
		datatype: gdal.Byte, gdal.GDT_UInt16, gdal.GDT_Float32
		"""
		if gt == "OMIGLOBAL025":
			cols = 1440
			rows = 720
			originX = -179.88
			originY = -89.88
			pixelWidth = 0.25
			pixelHeight = 0.25
		else:
			cols = array.shape[1]
			rows = array.shape[0]
			originX = gt[0]
			originY = gt[3]
			pixelWidth = gt[1]
			pixelHeight = gt[5]

		if len(array.shape) == 2:
			array = array[np.newaxis, :, :]
		bands = array.shape[0]

		# start writing from here.
		dr = gdal.GetDriverByName('GTiff') # register driver
		ds = dr.Create(fulloutpath, cols, rows, 1, datatype)
		ds.SetGeoTransform((originX, pixelWidth, 0, originY, 0, pixelHeight))
		# or you can do: ds.SetGeoTransform(gt)
		# setting the projection
		srs = osr.SpatialReference()
		try:
			srs.ImportFromEPSG(int(EPSGPROJCODE))
		except Exception as e:
			print(Exception, ":", e, " Can not found gcs.csv")
			p = Proj(init="epsg:" + str(EPSGPROJCODE))
			srs.ImportFromProj4(p.srs)
		ds.SetProjection(srs.ExportToWkt())

		for band in range(bands):
			outband = ds.GetRasterBand(band + 1)
			outband.WriteArray(array[band, :, :])
			outband.FlushCache()
		del(ds)

	def rio_write(self, array, fulloutpath, profile, dtype = rasterio.float64):
		count=profile["count"]
		# bug fix, can't write a 3D array having a shape like (1, *, *)
		if len(array.shape) == 3 and array.shape[0] == 1:
			array = array[0, :, :]
		profile.update(dtype = dtype, count = count, compress='lzw')
		with rasterio.open(fulloutpath, 'w', **profile) as dst:
			help(dst.write)
			dst.write(array.astype(dtype), count)


class Vector(object):
	"""docstring for Vector"""

	def __init__(self, vector_path):
		super(Vector, self).__init__()
		gdal.SetConfigOption('GDAL_FILENAME_IS_UTF8', 'NO')
		gdal.SetConfigOption('SHAPE_ENCODING', 'gb2312')
		try:
			self.path = vector_path.as_posix()
		except Exception as identifier:
			self.path = vector_path

	def __del__(self):
		pass

	def read(self):
		try:
			dataset = self.gpd_read_vetor()
		except Exception as identifier:
			dataset = self.ogr_read_shp()
		finally:
			return dataset

	def ogr_read_shp(self):
		ds = ogr.Open(self.path)
		count = ds.GetLayerCount()
		# print(dir(ds))
		# print(count)
		dataset = {}
		for lyrNum in range(count):
			layer = ds.GetLayer(lyrNum)
			layerDefn = layer.GetLayerDefn()
			spatialRef = layer.GetSpatialRef()  # spatial reference
			geomType = layerDefn.GetGeomType()  # geometry object type wkbPoint, wkbLineString, wkbPolygon
			# print(layerDefn, layerDefn.GetFieldCount())
			field_attrs = []
			field_names = []
			for fldNum in range(layerDefn.GetFieldCount()):
				field = layerDefn.GetFieldDefn(fldNum)
				# print(field.GetName())
				# print(dir(field))
				fieldName = field.GetName()
				fieldTypeCode = field.GetType()
				fieldType = field.GetFieldTypeName(fieldTypeCode)
				fieldWidth = field.GetWidth()
				GetPrecision = field.GetPrecision()
				field_names.append(fieldName)
				field_attrs.append({"fieldTypeCode": fieldTypeCode,
                                    "fieldType": fieldType,
                                    "fieldWidth": fieldWidth,
                                    "GetPrecision": GetPrecision})
			geometries = []
			for feature in layer:
				geometry = feature.GetGeometryRef().ExportToWkt()
				# print(geometry)
				# geometries.append(geometry)
				record = {}
				for fldNum in range(layerDefn.GetFieldCount()):
					field_name = field_names[fldNum]
					field_attr = field_attrs[fldNum]
					fieldval = feature.GetField(field_name)
					record[field_name] = {"val": fieldval, "attr": field_attr}
				geometries.append({"geometry": geometry, "attrlist": record})
				# print(dir(feature))
				# print(records)
				# # record = [feature.GetField(fldMeta["fieldName"]) for fldMeta in field_metas]
				# # print(record)
				# exit(0)
			dataset[layer.GetName()] = geometries
			dataset["spatialReference"] = spatialRef
			dataset["geometryType"] = geomType
		ds.Destroy()
		return dataset


	def gpd_read_vetor(self):
		gdf = geopandas.read_file(self.path)
		return gdf


	def write(self, gpd, fulloutpath):
		self.gpd_write_vetor(gpd, fulloutpath)
		# try:
		# 	self.gpd_write_vetor(gpd, fulloutpath)
		# except Exception as identifier:
		# 	print(identifier)
		# 	self.ogr_write_shp()


	def ogr_write_shp(self, dataset, fulloutpath, SPATIALREF = None, EPSGCODE = 4326, GEOMTYPE = None):
		# 有Bug,写出的shp在ArcGIS中不识别
		gdal.SetConfigOption('GDAL_FILENAME_IS_UTF8', 'NO')  # 解决中文路径
		gdal.SetConfigOption('SHAPE_ENCODING', 'gb2312')  # 解决 SHAPE 文件的属性值
		driver = ogr.GetDriverByName("ESRI Shapefile")
		if os.access(fulloutpath, os.F_OK):  # 如文件已存在，则删除
			driver.DeleteDataSource(fulloutpath)
		ds = driver.CreateDataSource(fulloutpath)  # 创建 Shape文件

		try:
			spatialRef = dataset["spatialReference"]
			dataset.pop("spatialReference")
			geomtype = dataset["geometryType"]
			dataset.pop("geometryType")
		except Exception as identifier:
			if SPATIALREF:
				spatialRef = SPATIALREF
			else:
				spatialRef = osr.SpatialReference()
				spatialRef.ImportFromEPSG(int(EPSGCODE))
			if GEOMTYPE:
				geomtype = GEOMTYPE
			else:
				geomtype = ogr.wkbPolygon
		for layerName, geometries in dataset.items():
			# print(layerName)
			layer = ds.CreateLayer(layerName, srs = spatialRef, geom_type = geomtype)  # 创建图层
			for geometryDict in geometries:
				# print(geometryDict)
				attrlist = geometryDict["attrlist"]
				for fieldName, meta in attrlist.items():
					try:
						field = ogr.FieldDefn(
							fieldName, self.ogr_type_code_mapping(meta["attr"]["fieldTypeCode"]))
					except Exception as identifier:
						try:
							field = ogr.FieldDefn(
								fieldName, ogr.OFTReal)
						except expression as identifier:
							field = ogr.FieldDefn(
								fieldName, ogr.OFTString)

					if "fieldWidth" in meta["attr"].keys():
						field.SetWidth(meta["attr"]["fieldWidth"])
					if "GetPrecision" in meta["attr"].keys():
						field.SetPrecision(meta["attr"]["GetPrecision"])
					# if "fieldType" in meta["attr"].keys():
					# 	field.SetType(meta["attr"]["fieldTypeCode"])
					field.SetName(fieldName)
					layer.CreateField(field)

				geomtry = ogr.CreateGeometryFromWkt(geometryDict["geometry"])
				feature = ogr.Feature(layer.GetLayerDefn())  # 创建 SF
				feature.SetGeometry(geomtry)
				for fieldName, meta in attrlist.items():
					feature.SetField(fieldName, meta["val"])
				layer.CreateFeature(feature)  # 将 SF 写入图层


		ds.Destroy()  # 关闭文件



		# for fd in fieldlist:  # 将字段列表写入图层
		# field = ogr.FieldDefn(fd['name'], fd['type'])
		# if fd.has_key('width'):
		# field.SetWidth(fd['width'])
		# if fd.has_key('decimal'):
		# field.SetPrecision(fd['decimal'])
		# layer.CreateField(field)
		# for i in range(len(reclist)):  # 将 SF 数据记录（几何对象及其属性写入图层）
		# geom = ogr.CreateGeometryFromWkt(geomlist[i])
		# feat = ogr.Feature(layer.GetLayerDefn())  # 创建 SF
		# feat.SetGeometry(geom)
		# for fd in fieldlist:
		# feat.SetField(fd['name'], reclist[i][fd['name']])
		# layer.CreateFeature(feat)  # 将 SF 写入图层
		# ds.Destroy()  # 关闭文件

	def ogr_type_code_mapping(self, type_code):
		# OFTInteger = 0, OFTIntegerList = 1, OFTReal = 2, OFTRealList = 3,
		# OFTString = 4, OFTStringList = 5, OFTWideString = 6, OFTWideStringList = 7,
		# OFTBinary = 8, OFTDate = 9, OFTTime = 10, OFTDateTime = 11
		ogr_type_dict = {
			"0": ogr.OFTInteger,
			"1": ogr.OFTIntegerList,
			"2": ogr.OFTReal,
			"3": ogr.OFTRealList,
			"4": ogr.OFTString,
			"5": ogr.OFTStringList,
			"6": ogr.OFTWideString,
			"7": ogr.OFTWideStringList,
			"8": ogr.OFTBinary,
			"9": ogr.OFTDate,
			"10": ogr.OFTTime,
			"11": ogr.OFTDateTime
		}

		return ogr_type_dict[str(type_code)]

	def gpd_write_vetor(self, gpd, fulloutpath):
		# filetype = fulloutpath.split('.')[-1]
		gpd.to_file(fulloutpath)

class Craftsman(object):
	def __init__(self, array):
		super(Craftsman, self).__init__()
		if type(array) == list:
			array = np.array(array)
		if len(array.shape) == 1:
			self.array = array[:, np.newaxis]
		else:
			self.array = array

	def __del__(self):
		pass

	def clean_array(self, FILLVAL = 0, SPECIFICVAL = None, AutoSelected = False):
		self.array[np.where(np.isnan(self.array) == True)] = FILLVAL
		self.array[np.where(np.isfinite(self.array) == False)] = FILLVAL
		if SPECIFICVAL:
			self.array[np.where(self.array == np.float64(SPECIFICVAL))] = FILLVAL
		elif AutoSelected:
			SPECIFICVAL = sorted([(np.sum(self.array == i), i)
						 for i in set(self.array.flat)])[-1][1]
			self.array[np.where(self.array == np.float64(SPECIFICVAL))] = FILLVAL
			SPECIFICVAL = None
		else:
			self.array[np.where(self.array <= 0)] = FILLVAL
	
	def flip_array(self, ROT = True, ROTANG = None, UPSIDEDOWN = False, LEFTSIDERIGHT = False):
		if ROT:
			# rotate clockwise 180
			self.array = self.array[::-1]

		if UPSIDEDOWN:
			# upside down
			nRow = self.array.shape[0]
			for row in range(nRow // 2):
				self.array[row], self.array[nRow-1 -
								i] = self.array[nRow-1-row], self.array[row]
		
		if LEFTSIDERIGHT:
			# leftside right
			nCol = self.array.shape[1]
			for each_row in self.array:
				for col in range(nCol // 2):
					each_row[col], each_row[nCol-1-col] = each_row[nCol-1-col], each_row[col]

		
			
		


# def main():
# 	raster = Raster('test.tif')
# 	raster.read()

if __name__ == '__main__':
	main()
	print("ok")

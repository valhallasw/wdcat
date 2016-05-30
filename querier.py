####################################################
# $Id$
####################################################
# MySQLdb command abstraction layer
# (C)2006,2016 by Merlijn 'valhallasw' van Deen [valhallasw at arctus dot nl]
#
# Licenced under the MIT license
# http://www.opensource.org/licenses/mit-license.php
####################################################
# Usage:
# ------
# import querier
# var = querier.querier(host="localhost", etc) #same as MySQLdb.connect attributes
# result = var.do("MySQL query")               #same as cursor.execute attributes
#
# all other functions are made purely for use on mediawiki tables.
#
# The result is a list of dictionaries: [{'colname': data1, 'colname2': data2},{'colname': data11, 'colname2': data22}]
####################################################

import MySQLdb, MySQLdb.cursors

# classes

class Querier:
  def __init__(self, verbose=False, mediawiki=False, **kwargs):
    
    self.counter = 0
    self.verbose = verbose
    self.mediawiki = mediawiki
      
    if 'read_default_file' not in kwargs:
        kwargs['read_default_file'] = '~/.my.cnf' #read toolserver database information (please make sure the host is listed in the file)

    kwargs['cursorclass'] = MySQLdb.cursors.DictCursor
    self.db = MySQLdb.connect(**kwargs)
  
  def do(self, sql, sqlargs, **kwargs):
    if not isinstance(sqlargs, (list, tuple)):
        raise TypeError
    transpose = kwargs.pop('transpose', False)
    if self.verbose:
       print repr((sql.replace("\n", " "), sqlargs))
 
    if self.mediawiki: 
      sqlargs = [x.encode('utf-8') if isinstance(x, unicode) else x
                 for x in sqlargs]
    cursor = self.db.cursor()
    cursor.execute(sql, sqlargs,**kwargs)
    retval = tuple(cursor.fetchall())
    cursor.close()
    self.counter = self.counter + 1

    if self.mediawiki:
      retval = map(self.doutf8, retval)

    if transpose:
      if len(retval) > 0:
        return dict(zip(retval[0].keys(),zip(*map(dict.values,retval))))
        # 17:36 < dodek> valhalla1w, you're posting it on obfuscated python coding contest or sth? :)
	# 17:36 < valhalla1w> actually i'm trying to transpose a list of dicts to a dict of lists
	# 17:42 < valhalla1w> s/list/tuple
      else:
        return {}

    return retval

  def doutf8(self, dictitem):
    for (name, item) in dictitem.iteritems():
      if isinstance(item, str) and name not in ["cl_sortkey"]:
        dictitem.update(dict([[name, item.decode('utf8')]]))

    return dictitem

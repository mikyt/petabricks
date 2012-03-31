import logging
import os
import sqlite3
import cStringIO as StringIO
import heuristic

logger = logging.getLogger(__name__)

class Error(Exception):
    #Base Exception class for this module
    pass

    
class HeuristicSetNotFoundError(Error):
    pass

class HeuristicNotFoundError(Error):
    pass

class KindNotFoundError(Error):
    pass

class HeuristicDB:
  def __init__(self, path=None):
      self._defer_commits = 0
      self._kindsCache = {}
      
      #Open DB    
      try:
          self._db = sqlite3.connect(self.computeDBPath(path))
      except:
          self._db = sqlite3.connect(":memory:")
      self._createTables()
        
    
  def _createTable(self, name, params):
    cur = self._db.cursor()
    query = "CREATE TABLE IF NOT EXISTS '"+name+"' "+params
    cur.execute(query)
    self.commit()
    cur.close()


    
  def _createTables(self):
    self._createTable("HeuristicKind", "('ID' INTEGER PRIMARY KEY AUTOINCREMENT, "
                                        "'name' TEXT UNIQUE, "
                                        "'resulttype' TEXT)")
    self._createTable("Heuristic", "('ID' INTEGER PRIMARY KEY AUTOINCREMENT, "
                      "'kindID' INTEGER, 'formula' TEXT, "
                      "'score' FLOAT, 'useCount' INTEGER,"
                      "FOREIGN KEY ('kindID') REFERENCES 'HeuristicKind' ('ID')"
                      "ON DELETE CASCADE ON UPDATE CASCADE)")
    self._createTable("HeuristicSet", "('ID' INTEGER PRIMARY KEY AUTOINCREMENT, "
                                       "'score' FLOAT, 'useCount' INTEGER)")
    self._createTable("InSet", "('setID' INTEGER, 'heuristicID' INTEGER,"
                      "FOREIGN KEY ('setID') REFERENCES 'HeuristicSet' ('ID') "
                      "ON DELETE CASCADE ON UPDATE CASCADE, "
                      "FOREIGN KEY ('heuristicID') REFERENCES 'Heuristic' ('ID')"
                      "ON DELETE CASCADE ON UPDATE CASCADE)")
    
    
  
  def defer_commits(self):
      """Allows to disable the execution of commits for all the subsequent 
      function calls until unlocked by calling undefer_commits().
      
      Useful for having faster execution of multiple instructions, by having
      them in a single transaction instead of many small transactions.
      
      This function can be called multiple times (to avoid problems
      when calling functions that defer commits on their own).
      The commits will be effectively executed when undefer_commits() is called
      a corresponding number of times."""
      self._defer_commits = self._defer_commits + 1
      
  def undefer_commits(self):
      """Reenable commits after they have been deferred.
      
      This function just re-enables the commit() method. It does not actually
      perform the commit"""
      assert self._defer_commits > 0
      self._defer_commits = self._defer_commits - 1
      
  def commit(self):
      if self._defer_commits > 0:
          return
          
      self._db.commit()
          
      
  def computeDBPath(self, path):
      if path:
          return os.path.abspath(path)
          
      dbPath= os.path.expanduser("~/tunerout/knowledge.db")
      return dbPath

      
  def getHeuristicKindID(self, kindName):
    """Return the ID of the specified kind.
    
    Uses a cache to make access faster"""
    try:
        return self._kindsCache[kindName]
    except KeyError:
        kind = self._getHeuristicKindIDFromDB(kindName)
        self._kindsCache[kindName] = kind
        return kind


  def _getHeuristicKindIDFromDB(self, kindName):
    cur = self._db.cursor()
    query = "SELECT ID From HeuristicKind WHERE name='"+kindName+"'"
    cur.execute(query)
    row = cur.fetchone()
    if row is None:
        raise KindNotFoundError
    kindID = row[0]
    cur.close()
    return kindID
  
  
  def storeHeuristicKind(self, kindName, resulttype):
    cur = self._db.cursor()
    query = "INSERT OR IGNORE INTO HeuristicKind ('name', 'resulttype') VALUES (?, ?)"
    cur.execute(query, (kindName, str(resulttype)))
    self.commit()
    cur.close()
    return self.getHeuristicKindID(kindName)
  
  
  def increaseHeuristicScore(self, heuristic, score):
    kindID=self.storeHeuristicKind(heuristic.name, heuristic.resulttype) 
    cur = self._db.cursor()
    query = "UPDATE Heuristic SET score=score+? WHERE kindID=? AND formula=?"
    cur.execute(query, (score, kindID, heuristic.formula))
    if cur.rowcount == 0:
      #There was no such heuristic in the DB: probably it was taken from the defaults
      query = "INSERT INTO Heuristic (kindID, formula, useCount, score) VALUES (?, ?, 1, ?)"
      cur.execute(query, (kindID, heuristic.formula, score))
    self.commit()
    cur.close()
  
  
  def increaseHeuristicUseCount(self, heuristic, uses=None):
    if uses is not None:
      count = uses
    else:
      count = heuristic.uses
    
    kindID=self.storeHeuristicKind(heuristic.name, heuristic.resulttype) 
    cur = self._db.cursor()
    query = "UPDATE Heuristic SET useCount=useCount+? WHERE kindID=? AND formula=?"
    cur.execute(query, (count, kindID, heuristic.formula))
    if cur.rowcount == 0:
      #There was no such heuristic in the DB: let's add it
      query = "INSERT INTO Heuristic (kindID, formula, useCount, score) VALUES (?, ?, 1, 0)"
      cur.execute(query, (kindID, heuristic.formula))
    self.commit()
    cur.close()
    
  
  def _valid_uses(self, heuristic):
    assert heuristic.uses is not None
    assert heuristic.tooLow is not None
    assert heuristic.tooHigh is not None
    
    uses = heuristic.uses
    outofbounds = heuristic.tooLow + heuristic.tooHigh
    return uses - outofbounds
      
  def markAsUsed(self, hSet, uses=None):
    """Mark a set of heuristics as used for generating a candidate executable"""
    
    self.defer_commits()
    
    #As single heuristics
    for name, heuristic in hSet.iteritems():
      self.increaseHeuristicUseCount(heuristic, uses)
      
    #As set
    if uses==None:
        uses=1
        
    try:
        setID = self._getHeuristicSetID(hSet)
        cur = self._db.cursor()
        query = ("UPDATE HeuristicSet SET useCount=useCount+1 WHERE ID=?")
        cur.execute(query, (setID, ))
        cur.close()
    except HeuristicSetNotFoundError:
        setID = self._storeNewHeuristicSetScore(hSet, score=0, 
                                                useCount=uses)
        
    self.undefer_commits()
    self.commit()
      
  def updateHSetWeightedScore(self, heuristicSet, points):
      self.defer_commits()
      self._updateHSetWeightedScore_asSingleHeuristics(heuristicSet, points)
      self._updateHSetScore(heuristicSet, points)
      self.undefer_commits()
      self.commit()
    
    
  def _updateHSetScore(self, heuristicSet, score):
      try:
          self._updateExistingHeuristicSetScore(heuristicSet, score)
      except HeuristicSetNotFoundError:
          self._storeNewHeuristicSetScore(heuristicSet, score, useCount=1)
  
  def _updateExistingHeuristicSetScore(self, heuristicSet, score):
      setID = self._getHeuristicSetID(heuristicSet)

      cur = self._db.cursor()
      query = "UPDATE HeuristicSet SET " \
            "score=((score*useCount)+?)/(useCount+1), " \
            "useCount=useCount+1 " \
            "WHERE ID=?"
      cur.execute(query, (score, setID))
      self.commit()
      cur.close()

      
  def _storeNewHeuristicSetScore(self, heuristicSet, score, useCount):
      cur = self._db.cursor()
      query = "INSERT INTO HeuristicSet (score, useCount) VALUES (?, ?)"
      cur.execute(query, (score, useCount))
      setID = cur.lastrowid
      self.defer_commits()
      self._storeNewHeuristicSet(heuristicSet, setID)
      self.undefer_commits()
      self.commit()
      cur.close()
      return setID
      
      
  def _storeNewHeuristicSet(self, heuristicSet, setID):
      cur = self._db.cursor()
      for heuristic in heuristicSet.itervalues():
          heuristicID = self.getHeuristicID(heuristic)
          query = "INSERT INTO InSet (setID, heuristicID) VALUES (?, ?)"
          cur.execute(query, (setID, heuristicID))
      self.commit()
      cur.close()
  
  
  def _getHeuristicSetID(self, heuristicSet):
      try:
          return self._getHeuristicSetID_unchecked(heuristicSet)
      except HeuristicNotFoundError:
          raise HeuristicSetNotFoundError        
  
  
  def _getHeuristicSetID_unchecked(self, heuristicSet):
      if hasattr(heuristicSet, "ID"):
          #Result already cached!
          return heuristicSet.ID
          
      heuristicIDList = self._getHeuristicIDList(heuristicSet)
      cur = self._db.cursor()
      query = ("SELECT setID FROM InSet WHERE setID IN ("
               "  SELECT setID FROM InSet WHERE heuristicID IN %s"
               "  GROUP BY setID"
               "  HAVING COUNT(*)=%d )"
               " GROUP BY setID"
               " HAVING COUNT(*)=%d") % (self._getSQLList(heuristicIDList), 
                                         len(heuristicIDList),
                                         len(heuristicIDList))
      cur.execute(query)
      row = cur.fetchone()
      try:
          result = row[0]
          
          #Cache in the object
          heuristicSet.ID = result
          logger.debug("HeuristicSet: ID=%s, type=%s", result, type(result))
          return result
      except TypeError:
          raise HeuristicSetNotFoundError
      finally:
          cur.close()
  
  
  def _getHeuristicIDList(self, heuristicSet):
      heuristicIDList = []
      for heuristic in heuristicSet.itervalues():
          ID = self.getHeuristicID(heuristic)
          heuristicIDList.append(ID)
      return heuristicIDList
  
  
  def getHeuristicID(self, heuristic):
    kindID = self.getHeuristicKindID(heuristic.name)
    cur = self._db.cursor()
    query = "SELECT ID From Heuristic WHERE kindID=? AND formula=?"
    cur.execute(query, (kindID, heuristic.formula))
    try:
        kindID = cur.fetchone()[0]
        return kindID
    except:
        raise HeuristicNotFoundError(heuristic)
    finally:
        cur.close()

  def _updateHSetWeightedScore_asSingleHeuristics(self, heuristicSet, points):
      for name, heuristic in heuristicSet.iteritems():
          self.updateHeuristicWeightedScore(heuristic, points)
      
  
  def updateHeuristicWeightedScore(self, heuristic, points):
    """The new score of the heuristic is given by the weighted average of the 
    current score and the new score.
    The weight is modified in such a way that only valid uses actively 
    contribute to the final score
    
    finalScore = ((oldScore*oldUses) + (newScore*newValidUses)) / (oldUses+newUses)
    finalUses = oldUses + newUses"""
    newScore = points
    newValidUses = self._valid_uses(heuristic)
    newUses = heuristic.uses
    
    logger.debug("UPDATING Heuristic")
    logger.debug(heuristic)
    logger.debug("newScore=%f, newUses=%d, newValidUses=%d", newScore, newUses, 
                                                              newValidUses)
    
    kindID=self.storeHeuristicKind(heuristic.name, heuristic.resulttype) 
    cur = self._db.cursor()
    query = "UPDATE Heuristic SET " \
            "score=((score*useCount)+(?*?))/(useCount+?), " \
            "useCount=useCount+? " \
            "WHERE kindID=? AND formula=?"
    cur.execute(query, (newScore, newValidUses, newUses, newUses, kindID, 
                        heuristic.formula))
    if cur.rowcount == 0:
      #There was no such heuristic in the DB: let's add it
      query = "INSERT INTO Heuristic (kindID, formula, useCount, score) VALUES (?, ?, ?, ?)"
      logger.debug("The heuristic is actually new!")
      cur.execute(query, (kindID, heuristic.formula, heuristic.uses, 
                          (newScore*newValidUses)/newUses))
    self.commit()
    cur.close()
    
    
  def getBestNHeuristics(self, name, N):
      """Returns (finalScore, heuristic) pairs, ordered by finalScore"""
      cur = self._db.cursor()
      query = ("SELECT score, formula"
               " FROM Heuristic JOIN HeuristicKind"
               " ON Heuristic.kindID=HeuristicKind.ID"
               " WHERE HeuristicKind.name=?"
               " ORDER BY score DESC LIMIT ?")
      cur.execute(query, (name, N))
      result = [(row[0], row[1]) for row in cur.fetchall()]
      cur.close()
      return result


  def getNMostFrequentHeuristics(self, name, N, threshold=1):
      """Returns (finalScore, heuristic) pairs, ordered by number of uses
and then by score. The score must be greater than the given threshold"""
      cur = self._db.cursor()
      query = ("SELECT score, formula FROM Heuristic"
               " JOIN HeuristicKind ON Heuristic.kindID=HeuristicKind.ID"
               " WHERE HeuristicKind.name=? AND score>?"
               " ORDER BY Heuristic.useCount DESC,"
               "  score DESC"
               " LIMIT ?")
      cur.execute(query, (name, threshold, N))
      result = [(row[0], row[1]) for row in cur.fetchall()]
      cur.close()
      return result
  
  
  def getNBestHeuristicSubsetID(self, neededHeuristics, N, threshold=1):
      """Returns (score, hsetID) pairs, ordered by score. 
      The score must be greater than the given threshold"""
      subsetIDs = self.getHeuristicSubsetsIDs(neededHeuristics)
      
      cur = self._db.cursor()
      query = ("SELECT score, ID FROM HeuristicSet WHERE ID IN %s AND score>=?"
               " ORDER BY score DESC"
               " LIMIT ?") % self._getSQLList(subsetIDs)
      cur.execute(query, (threshold, N))
      result = [(row[0], row[1]) for row in cur.fetchall()]
      cur.close()
      return result
          
      
  def getHeuristicsScoreByKind(self, kind, bestN=None):
    """Return a dictionary {formula : score}, 
    for all the heuristics of the given kind"""
    cur = self._db.cursor()
    query = "SELECT formula, score FROM Heuristic "\
	    "JOIN HeuristicKind ON Heuristic.kindID=HeuristicKind.ID " \
	    "WHERE HeuristicKind.name=? "
    if bestN is not None:
      query=query+" ORDER BY score DESC LIMIT "+str(int(bestN))
      
    cur.execute(query, (kind,))
    result = {}
    for row in cur.fetchall():
      result[row[0]] = row[1]
    cur.close()
    return result

  def getHeuristicSet(self, ID):
      cur = self._db.cursor()
      query = ("SELECT name, formula, resulttype FROM Heuristic"
               " JOIN InSet ON Heuristic.ID = InSet.heuristicID"
               " JOIN HeuristicKind ON Heuristic.kindID = HeuristicKind.ID"
               " WHERE setID=?")
      cur.execute(query, (ID,))
      
      hset = heuristic.HeuristicSet()
      hset.ID = ID
      for row in cur.fetchall():
          name = row[0]
          formula = row[1]
          resulttype = row[2]
          hset[name] = heuristic.Heuristic(name, formula, resulttype)
      
      return hset
      
  
  def addAsFavoriteCandidates(self, heuristicSets, maximumScore=1):
    """Adds all the heuristics sets contained in "heuristicSets" to the 
database, with maximum score, so that they will be selected with maximum likelihood"""
    self.defer_commits()
    for hSet in heuristicSets:
      self.markAsUsed(hSet, 1)
      self.addToScore(hSet, maximumScore)
    self.undefer_commits()
    self.commit()
  
  
  def addToScore(self, hSet, score):
    """Increase the score of a set of heuristics by the given amount"""
    
    #As single heuristics
    for name, heuristic in hSet.iteritems():
        self.increaseHeuristicScore(heuristic, score)
    
    #As set
    setID = self._getHeuristicSetID(hSet)
    cur = self._db.cursor()
    query = ("UPDATE HeuristicSet SET score=score WHERE ID=?")
    cur.execute(query, setID)
    self.commit()
    cur.close()
    
      
      
  def getHeuristicSubsetsIDs(self, neededHeuristics):
      """Returns a list containig the IDs of the sets of heuristics that contain
      a subset of the needed heuristics"""
      kindslist = self._getSQLList(self._getKindsList(neededHeuristics))
      cur = self._db.cursor()
      query = ("SELECT DISTINCT setID FROM InSet JOIN Heuristic"
               " ON InSet.heuristicID = Heuristic.ID"
               " WHERE kindID IN %s"
               " EXCEPT"
               " SELECT DISTINCT setID FROM InSet JOIN Heuristic"
               "  ON InSet.heuristicID = Heuristic.ID"
               "  WHERE kindID NOT IN %s"
               ) % (kindslist, kindslist)
      cur.execute(query)
      result = [row[0] for row in cur.fetchall()]
      cur.close()
      return result
      
  
  def _getKindsList(self, neededHeuristics):
      """Get the list of IDs of kinds contained in the neededHeuristics.
      If an kind is not available, exclude it and return a subset of the IDs."""
      kinds = []
      for heuristic in neededHeuristics:
          try:
              kind = self.getHeuristicKindID(heuristic.name)
              kinds.append(kind)
          except KindNotFoundError:
              #Exclude this kind
              pass
      return kinds
  
  def _getSQLList(self, elemlist):
      output = StringIO.StringIO()
      output.write("(")
      count = 0
      for elem in elemlist:
          count = count+1
          if count != 1:
              output.write(", ")
          output.write(str(elem))
      output.write(")")
      sqlstr = output.getvalue()
      return sqlstr
    
  def close(self):
    self._db.close()
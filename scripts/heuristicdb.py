import sqlite3
import os

class HeuristicDB:
  def __init__(self):
    #Open DB    
    try:
      self.__db = sqlite3.connect(self.computeDBPath())
    except:
      self.__db = sqlite3.connect(":memory:")
    self.__createTables()
    self.__createView("HeuristicsRank", 
          "SELECT *, "
          "Heuristic.score/Heuristic.useCount as finalScore "
          "FROM Heuristic "
          "ORDER BY Heuristic.score/Heuristic.useCount")
    
  def __createTable(self, name, params):
    cur = self.__db.cursor()
    query = "CREATE TABLE IF NOT EXISTS '"+name+"' "+params
    cur.execute(query)
    self.__db.commit()
    cur.close()

    
  def __createView(self, name, params):
    cur = self.__db.cursor()
    query = "CREATE VIEW IF NOT EXISTS '"+name+"' AS "+params
    cur.execute(query)
    self.__db.commit()
    cur.close()

    
  def __createTables(self):
    self.__createTable("HeuristicKind", "('ID' INTEGER PRIMARY KEY AUTOINCREMENT, "
                                        "'name' TEXT UNIQUE)")
    self.__createTable("Heuristic", "('kindID' INTEGER, 'formula' TEXT, "
                                    "'useCount' INTEGER, 'score' FLOAT,"
                                    "PRIMARY KEY (kindID, formula), "
                                    "FOREIGN KEY ('kindID') REFERENCES 'HeuristicKind' ('ID')"
                                    "ON DELETE CASCADE ON UPDATE CASCADE)")
    #TODO:self.__createTable("InSet", "('setID' INTEGER, 'heuristicID' INTEGER)"
    
  def computeDBPath(self):
    #TODO: make the path more flexible
    dbPath= os.path.expanduser("~/tunerout/knowledge.db")
    return dbPath

  def getHeuristicKindID(self, kindName):
    cur = self.__db.cursor()
    query = "SELECT ID From HeuristicKind WHERE name='"+kindName+"'"
    cur.execute(query)
    kindID = cur.fetchone()[0]
    cur.close()
    return kindID
  
  
  def storeHeuristicKind(self, kindName):
    cur = self.__db.cursor()
    query = "INSERT OR IGNORE INTO HeuristicKind ('name') VALUES ('"+kindName+"')"
    cur.execute(query)
    self.__db.commit()
    cur.close()
    return self.getHeuristicKindID(kindName)
  
  
  def increaseHeuristicScore(self, name, formula, score):
    kindID=self.storeHeuristicKind(name) 
    cur = self.__db.cursor()
    query = "UPDATE Heuristic SET score=score+? WHERE kindID=? AND formula=?"
    cur.execute(query, (score, kindID, formula))
    if cur.rowcount == 0:
      #There was no such heuristic in the DB: probably it was taken from the defaults
      query = "INSERT INTO Heuristic (kindID, formula, useCount, score) VALUES (?, ?, 1, ?)"
      cur.execute(query, (kindID, formula, score))
    self.__db.commit()
    cur.close()
  
  
  def increaseHeuristicUseCount(self, heuristic, uses=None):
    if uses is not None:
      count = uses
    else:
      count = heuristic.uses
    
    kindID=self.storeHeuristicKind(heuristic.name) 
    cur = self.__db.cursor()
    query = "UPDATE Heuristic SET useCount=useCount+? WHERE kindID=? AND formula=?"
    cur.execute(query, (count, kindID, heuristic.formula))
    if cur.rowcount == 0:
      #There was no such heuristic in the DB: let's add it
      query = "INSERT INTO Heuristic (kindID, formula, useCount, score) VALUES (?, ?, 1, 0)"
      cur.execute(query, (kindID, heuristic.formula))
    self.__db.commit()
    cur.close()
    
  
  def _computeScore(self, heuristic, points):
    uses = heuristic.uses
    outofbounds = heuristic.tooLow + heuristic.tooHigh
    return points * (uses - outofbounds)
    
  def addToScore(self, hSet, points, weightedScore=True):
    """Increase the score of a set of heuristics by the given amount"""
    #TODO: also store it as a set
      
    for name, heuristic in hSet.iteritems():
      if weightedScore:
	outofbounds = heuristic.tooHigh + heuristic.tooLow
	uses = heuristic.uses 
	score = self._computeScore(heuristic, points)
      else:
	score = points
      
      self.increaseHeuristicScore(name, heuristic.formula, score)
      
      
  def markAsUsed(self, hSet, uses=None):
    """Mark a set of heuristics as used for generating a candidate executable"""
    #TODO: also store it as a set
    for name, heuristic in hSet.iteritems():
      self.increaseHeuristicUseCount(heuristic, uses)

  def updateHSetWeightedScore(self, heuristicSet, points):
    #TODO: also store it as a set
    for name, heuristic in heuristicSet.iteritems():
      self.updateHeuristicWeightedScore(heuristic, points)
    
  def updateHeuristicWeightedScore(self, heuristic, points):
    """The new score of the heuristic is given by the average of the current score and the new score,
    rescaled in such a way to have the use count equal to the sum of the use count of the old and new scores:
    
    finalScore = ((oldScore/oldUses) + (newScore/newUses))/2 * (oldUses+newUses)
    finalUses = oldUses + newUses"""
    newScore = self._computeScore(heuristic, points)
    newUses = heuristic.uses
    
    print "UPDATING Heuristic"
    print heuristic
    print "newScore: %f" % newScore
    
    kindID=self.storeHeuristicKind(heuristic.name) 
    cur = self.__db.cursor()
    query = "UPDATE Heuristic SET " \
            "score=((score/useCount)+(?/?))/2 *(useCount+?), " \
            "useCount=useCount+? " \
            "WHERE kindID=? AND formula=?"
    cur.execute(query, (newScore, newUses, newUses, newUses, kindID, heuristic.formula))
    if cur.rowcount == 0:
      #There was no such heuristic in the DB: let's add it
      query = "INSERT INTO Heuristic (kindID, formula, useCount, score) VALUES (?, ?, ?, ?)"
      print "NEW!!!"
      cur.execute(query, (kindID, heuristic.formula, heuristic.uses, newScore))
    self.__db.commit()
    cur.close()
    
    
    
    
  def getBestNHeuristics(self, name, N):
    cur = self.__db.cursor()
    query = "SELECT formula FROM Heuristic JOIN HeuristicKind ON Heuristic.kindID=HeuristicKind.ID WHERE HeuristicKind.name=? ORDER BY Heuristic.score/Heuristic.useCount DESC LIMIT ?"
    cur.execute(query, (name, N))
    result = [row[0] for row in cur.fetchall()]
    cur.close()
    return result
  
  
  def getHeuristicsFinalScoreByKind(self, kind):
    """Return a dictionary {formula : finalScore}, 
    where finalScore=score/useCount, for all the heuristics of the given kind"""
    cur = self.__db.cursor()
    query = "SELECT formula, score/useCount FROM Heuristic "\
	    "JOIN HeuristicKind ON Heuristic.kindID=HeuristicKind.ID " \
	    "WHERE HeuristicKind.name=? "
    cur.execute(query, (kind,))
    result = {row[0]:row[1] for row in cur.fetchall()}
    cur.close()
    return result

    
  def addAsFavoriteCandidates(self, heuristicSets, maximumScore=1):
    """Adds all the heuristics sets contained in "heuristicSets" to the 
database, with maximum score, so that they will be selected with maximum likelihood"""
    for hSet in heuristicSets:
      self.markAsUsed(hSet, 1)
      self.addToScore(hSet, maximumScore, weightedScore=False)
      
  def close(self):
    self.__db.close()
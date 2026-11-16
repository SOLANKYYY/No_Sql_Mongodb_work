// Run these in Neo4j Browser after RUN_16.ps1.
MATCH (s:E16Student)-[r:ENROLLED_IN]->(c:E16Course) RETURN s,r,c;
MATCH (:E16Student {id:'S1'})-[:ENROLLED_IN]->(c:E16Course) RETURN c.id,c.title;
MATCH (s:E16Student)-[:ENROLLED_IN]->(:E16Course {id:'C1'}) RETURN s.id,s.name;
MATCH (a:E16Student {id:'S1'})-[:ENROLLED_IN]->(:E16Course)<-[:ENROLLED_IN]-(b:E16Student)
WHERE a<>b RETURN DISTINCT b.id,b.name;
MATCH (:E16Course {id:'C3'})-[:REQUIRES*1..5]->(p:E16Course) RETURN DISTINCT p.id,p.title;
MATCH p=(a:E16User {id:'U1'})-[:TRANSFERRED_TO*1..3]-(b:E16User)
WHERE a<>b RETURN b.id,min(length(p)) AS hops ORDER BY hops;
MATCH p=(a:E16User {id:'U1'})-[:TRANSFERRED_TO*2..3]->(a) RETURN p;

// Explicit checks work in mongosh without MongoDB's internal test helpers.
function commandSucceeded(result) {
  if (!result || Number(result.ok) !== 1 || result.writeConcernError ||
      (result.writeErrors && result.writeErrors.length)) {
    throw new Error('MongoDB command did not succeed: ' + JSON.stringify(result));
  }
  return result;
}
const hosts = process.env.RS_HOSTS;
const uri='mongodb://'+encodeURIComponent(process.env.MONGO_ADMIN_USER)+':'+
  encodeURIComponent(process.env.MONGO_ADMIN_PASSWORD)+'@'+hosts+'/admin?replicaSet=rs0&authSource=admin';
const c = new Mongo(uri);
const admin=c.getDB('admin');
const coll=c.getDB('exercise13').sentinel;
const action=process.env.CHECK_ACTION || 'status';
if(action==='seed') commandSucceeded(c.getDB('exercise13').runCommand({
  update:'sentinel',updates:[{q:{_id:'k8s-persistence'},u:{$set:{value:'survives-pod-recreation'}},upsert:true}],
  writeConcern:{w:3,wtimeout:30000}
}));
const s=admin.runCommand({replSetGetStatus:1});
commandSucceeded(s);
const members=s.members.map(m=>({name:m.name,state:m.stateStr,health:m.health}));
if(members.length!==3 || members.filter(m=>m.state==='PRIMARY').length!==1 ||
   members.filter(m=>m.state==='SECONDARY').length!==2 || members.some(m=>m.health!==1))
  throw new Error('Replica set not healthy yet');
// Read directly from mongo-2, so evidence proves the recreated member contains the document.
const target=new Mongo('mongodb://'+encodeURIComponent(process.env.MONGO_ADMIN_USER)+':'+
  encodeURIComponent(process.env.MONGO_ADMIN_PASSWORD)+'@'+hosts.split(',')[2]+'/admin?directConnection=true&authSource=admin');
target.setReadPref('secondaryPreferred');
const sentinel=target.getDB('exercise13').sentinel.findOne({_id:'k8s-persistence'});
if(!sentinel || sentinel.value!=='survives-pod-recreation') throw new Error('Sentinel missing on mongo-2');
print(JSON.stringify({passed:true,members,sentinel:sentinel.value,directReadMember:hosts.split(',')[2]}));

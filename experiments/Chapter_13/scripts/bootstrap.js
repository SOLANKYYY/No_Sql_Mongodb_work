// Explicit checks work in mongosh without MongoDB's internal test helpers.
function commandSucceeded(result) {
  if (!result || Number(result.ok) !== 1 || result.writeConcernError ||
      (result.writeErrors && result.writeErrors.length)) {
    throw new Error('MongoDB command did not succeed: ' + JSON.stringify(result));
  }
  return result;
}
// Executed INSIDE mongo1/mongo-0, through loopback: required by localhost exception.
const hosts = process.env.RS_HOSTS.split(',');
const user = process.env.MONGO_ADMIN_USER;
const password = process.env.MONGO_ADMIN_PASSWORD;
const local = db.getSiblingDB('admin');
function authenticationSucceeded(result) {
  return result === true || result === 1 || (result && Number(result.ok) === 1);
}
let authenticated = false;
try { authenticated = authenticationSucceeded(local.auth(user, password)); } catch (e) {}
if (!authenticated) {
  let state;
  try {
    state = local.runCommand({replSetGetStatus: 1});
  } catch (error) {
    // mongosh throws for an uninitialized replica set instead of returning {ok:0}.
    // Only this expected first-run condition permits initiation.
    if (error.code !== 94 && error.codeName !== 'NotYetInitialized') throw error;
    state = {ok: 0, code: 94};
  }
  if (state.code === 94) {
    commandSucceeded(local.runCommand({replSetInitiate: {
      _id: 'rs0', members: hosts.map((host, i) => ({_id:i, host, priority:i===0?2:1}))
    }}));
  } else if (!state.ok) {
    throw new Error('Bootstrap refused: existing users or unexpected state. Keep the original .env.');
  }
  let ready = false;
  for(let i=0; i<120; i++) {
    if(local.runCommand({hello:1}).isWritablePrimary) { ready=true; break; }
    sleep(1000);
  }
  if(!ready) throw new Error('Local bootstrap node did not become primary within 120 seconds.');
  local.createUser({user, pwd:password, roles:[{role:'root',db:'admin'}]});
  if (!authenticationSucceeded(local.auth(user,password))) throw new Error('Administrator authentication failed after creation.');
}
const uri = 'mongodb://' + encodeURIComponent(user) + ':' + encodeURIComponent(password) +
  '@' + hosts.join(',') + '/admin?replicaSet=rs0&authSource=admin';
const admin = new Mongo(uri).getDB('admin');
if(!admin.getUser('labuser')) admin.createUser({user:'labuser',pwd:process.env.MONGO_APP_PASSWORD,
  roles:[{role:'readWrite',db:'exercise13'}]});
if(!admin.getUser('monitor')) admin.createUser({user:'monitor',pwd:process.env.MONGO_MONITOR_PASSWORD,
  roles:[{role:'clusterMonitor',db:'admin'}]});
const status=admin.runCommand({replSetGetStatus:1});
commandSucceeded(status);
print(JSON.stringify({bootstrap:'complete',members:status.members.map(m=>({name:m.name,state:m.stateStr}))}));

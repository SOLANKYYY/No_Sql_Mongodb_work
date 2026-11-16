param([string]$ProjectPath = (Get-Location).Path)
$ErrorActionPreference = 'Stop'
$ProjectPath = [System.IO.Path]::GetFullPath($ProjectPath)
foreach ($relative in @('START.ps1','LAB13_2.ps1','scripts/bootstrap.js','scripts/k8s-check.js','k8s/02-scripts.yaml')) {
    if (-not (Test-Path (Join-Path $ProjectPath $relative))) {
        throw "Missing $relative. Run this repair from the project folder containing START.ps1."
    }
}
$bootstrap = @'
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

'@
$check = @'
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

'@
$utf8 = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $ProjectPath 'scripts/bootstrap.js'), $bootstrap, $utf8)
[System.IO.File]::WriteAllText((Join-Path $ProjectPath 'scripts/k8s-check.js'), $check, $utf8)
$config = [ordered]@{
    apiVersion = 'v1'; kind = 'ConfigMap'
    metadata = [ordered]@{ name = 'mongo-scripts'; namespace = 'exercise13' }
    data = [ordered]@{ 'bootstrap.js' = $bootstrap; 'k8s-check.js' = $check }
}
[System.IO.File]::WriteAllText((Join-Path $ProjectPath 'k8s/02-scripts.yaml'), ($config | ConvertTo-Json -Depth 8), $utf8)
foreach ($name in @('START.ps1','LAB13_2.ps1')) {
    $path = Join-Path $ProjectPath $name
    $text = [System.IO.File]::ReadAllText($path)
    $text = $text.Replace("'--quiet','/scripts/bootstrap.js'", "'--quiet','--file','/scripts/bootstrap.js'")
    $text = $text.Replace('mongosh --quiet /scripts/k8s-check.js', 'mongosh --quiet --file /scripts/k8s-check.js')
    [System.IO.File]::WriteAllText($path, $text, $utf8)
}
Write-Host 'MONGOSH REPAIR V2 COMPLETE'
Write-Host 'Removed test-helper dependencies from both labs and synchronized the Kubernetes ConfigMap.'
Write-Host 'Credentials, results, and database volumes were preserved.'
Write-Host 'Next: powershell -NoProfile -ExecutionPolicy Bypass -File .\START.ps1'

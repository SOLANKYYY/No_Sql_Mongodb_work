"""Snapshot rollback, controlled oplog point-in-time recovery, timings and scheduling."""
import csv,tempfile
from core import *

def seed(coll,n,payload_bytes=900):
    # Only dedicated test collections are passed by the callers below.
    from bson import BSON
    coll.drop();stamp=datetime.now(timezone.utc);total=0
    for start in range(0,n,1000):
        docs=[{'_id':i,'sequence':i,'value':i*7,'verified':False,'created_at':stamp,'payload':hashlib.sha256(str(i).encode()).hexdigest()*(payload_bytes//64)+('x'*(payload_bytes%64))} for i in range(start,min(start+1000,n))]
        total+=sum(len(BSON.encode(d)) for d in docs);coll.insert_many(docs,ordered=True)
    return total

def snapshot_test(c):
    coll=c[DB].backup_test;seed(coll,1000);before=checksum(coll)
    folder,meta=backup_once();coll.update_many({}, {'$set':{'verified':True,'value':-1}})
    changed=checksum(coll);assert changed['sha256']!=before['sha256']
    started=time.perf_counter();restore_seconds=run_tool('mongorestore',SOURCE,['--drop','--stopOnError','--gzip','--nsInclude',DB+'.backup_test',folder/'dump'])
    after=checksum(coll);ready=coll.find_one({'_id':0}) is not None;total=time.perf_counter()-started
    result={'timestamp':utc(),'documents':1000,'before':before,'modified':changed,'after':after,'backup_seconds':meta['seconds'],'restore_seconds':restore_seconds,
            'recovery_verified_seconds':total,'application_read_ready':ready,'passed':before==after and ready,'backup_directory':folder.name}
    save('lab14_2_restore.json',result)
    if not result['passed']:raise RuntimeError('Snapshot integrity mismatch.')

def pitr_test(c):
    """Controlled no-concurrent-writer drill. Not a general continuous PITR service."""
    from bson import BSON
    assert_lab(SOURCE);assert_lab(TARGET)
    with client(TARGET) as target:
        target.admin.command('ping');coll=c.exercise14_pitr.timeline;coll.drop()
        coll.insert_many([{'_id':i,'stage':'base','value':i} for i in range(10)])
        folder=BACKUPS/('pitr-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'));folder.mkdir(parents=True)
        # Full replica-set dump with oplog: no --db or namespace filters.
        dump_seconds=run_tool('mongodump',SOURCE,['--oplog','--out',folder/'dump'])
        oplog=c.local['oplog.rs'];anchor=oplog.find_one(sort=[('$natural',-1)])['ts']
        coll.update_one({'_id':0},{'$set':{'stage':'approved','value':999}})
        good_ts=oplog.find_one({'ns':'exercise14_pitr.timeline'},sort=[('$natural',-1)])['ts']
        expected=checksum(coll)
        coll.update_one({'_id':0},{'$set':{'stage':'corrupted','value':-999}})
        bad_ts=oplog.find_one({'ns':'exercise14_pitr.timeline'},sort=[('$natural',-1)])['ts']
        if not anchor<good_ts<bad_ts:raise RuntimeError('PITR timestamp sequence was not valid.')
        entries=list(oplog.find({'ts':{'$gt':anchor,'$lte':bad_ts}}).sort('$natural',1))
        if not any(x['ts']==good_ts for x in entries) or not any(x['ts']==bad_ts for x in entries):raise RuntimeError('Required oplog range missing.')
        # Preserve dump-time oplog entries and append the captured post-dump range in order.
        with (folder/'dump/oplog.bson').open('ab') as stream:
            for entry in entries:stream.write(BSON.encode(entry))
        limit=f'{bad_ts.time}:{bad_ts.inc}'
        target.drop_database('exercise14_pitr')
        started=time.perf_counter()
        seconds=run_tool('mongorestore',TARGET,['--drop','--preserveUUID','--stopOnError','--oplogReplay','--oplogLimit',limit,folder/'dump'])
        restored=checksum(target.exercise14_pitr.timeline);doc=target.exercise14_pitr.timeline.find_one({'_id':0});ready=bool(doc and doc['stage']=='approved')
        result={'timestamp':utc(),'method':'full mongodump --oplog + captured post-dump range + mongorestore --oplogReplay --oplogLimit',
                'scope':'controlled dedicated lab; no concurrent application writers','good_write_timestamp':f'{good_ts.time}:{good_ts.inc}',
                'excluded_bad_write_timestamp':limit,'captured_post_dump_entries':len(entries),'backup_seconds':dump_seconds,
                'restore_seconds':seconds,'recovery_verified_seconds':time.perf_counter()-started,'expected':expected,'restored':restored,
                'good_write_included':ready,'bad_write_excluded':bool(doc and doc['stage']!='corrupted'),
                'passed':restored==expected and ready,'backup_directory':folder.name}
        save('lab14_2_pitr.json',result)
        if not result['passed']:raise RuntimeError('Point-in-time recovery failed verification.')

def benchmarks(c):
    rows=[];coll=c[DB].benchmark
    for n in (1000,10000,100000):
        print(f'BENCHMARK: {n:,} documents - seeding, backup, modification and restore',flush=True)
        logical_bytes=seed(coll,n);before=checksum(coll)
        # Delete only this transient benchmark archive after a successful integrity check.
        with tempfile.TemporaryDirectory(prefix='benchmark-',dir=BACKUPS) as temp:
            folder=Path(temp);archive=folder/'benchmark.archive.gz'
            backup_s=run_tool('mongodump',SOURCE,['--db',DB,'--collection','benchmark','--gzip','--archive='+str(archive)])
            archive_bytes=archive.stat().st_size;coll.update_many({}, {'$set':{'verified':True,'value':-1}})
            started=time.perf_counter();restore_s=run_tool('mongorestore',SOURCE,['--drop','--stopOnError','--nsInclude',DB+'.benchmark','--gzip','--archive='+str(archive)])
            after=checksum(coll);ready=coll.find_one({'_id':0}) is not None;verified_s=time.perf_counter()-started
            row={'documents':n,'logical_bson_bytes':logical_bytes,'compressed_backup_bytes':archive_bytes,'backup_seconds':backup_s,'restore_seconds':restore_s,
                 'recovery_verified_seconds':verified_s,'rpo_schedule_seconds':3600,'before':before,'after':after,'passed':before==after and ready}
            rows.append(row);print(json.dumps(row,indent=2),flush=True)
            if not row['passed']:raise RuntimeError('Benchmark restore checksum mismatch.')
    coll.drop()
    result={'timestamp':utc(),'passed':all(x['passed'] for x in rows),'rows':rows,
            'rpo_note':'Hourly successful snapshots imply nominal exposure of up to one hour; completion time, scheduling delays and failures can increase it.',
            'rto_note':'Restore seconds and restore-plus-integrity/read-readiness seconds are measured. No full application restart or infrastructure replacement is included.'}
    save('lab14_2_benchmarks.json',result)
    with (RESULTS/'benchmark_timings.csv').open('w',newline='') as out:
        fields=['documents','logical_bson_bytes','compressed_backup_bytes','backup_seconds','restore_seconds','recovery_verified_seconds','rpo_schedule_seconds','passed']
        writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(rows)

def retention_test():
    now=datetime.now(timezone.utc)
    with tempfile.TemporaryDirectory(prefix='retention-test-',dir=BACKUPS) as temp:
        root=Path(temp)
        labels={}
        for label,age,complete in [('old',8,True),('recent',1,True),('boundary',7,True),('incomplete',9,False)]:
            stamp=now-timedelta(days=age);path=root/('backup-'+stamp.strftime('%Y%m%dT%H%M%S%fZ'));path.mkdir();labels[label]=path
            write_json(path/'manifest.json',{'kind':'exercise14-backup','completed':complete,'completed_at':stamp.isoformat()})
        unrelated=root/'other-data';unrelated.mkdir()
        removed=retention(root,now)
        checks={'old_completed_removed':not labels['old'].exists(),'recent_kept':labels['recent'].exists(),'boundary_kept':labels['boundary'].exists(),'incomplete_kept':labels['incomplete'].exists(),'unrelated_kept':unrelated.exists()}
        save('lab14_2_retention.json',{'timestamp':utc(),'evidence_type':'temporary fixture folders using the real cleanup function','days':7,'checks':checks,'passed':all(checks.values())})
        if not all(checks.values()):raise RuntimeError('Retention test failed.')

def lab():
    BACKUPS.mkdir(parents=True,exist_ok=True)
    assert_lab(SOURCE)
    with client() as c:
        c.admin.command('ping');snapshot_test(c);pitr_test(c);benchmarks(c)
    retention_test()

def schedule(interval=3600,cycles=0):
    if interval<=0:raise ValueError('Positive schedule interval required.')
    count=0;next_start=time.monotonic()
    while cycles==0 or count<cycles:
        start=time.monotonic()
        status={'timestamp':utc(),'configured_interval_seconds':interval,'retention_days':7,'status':'running'}
        write_json(RESULTS/'scheduler_status.json',status)
        try:
            folder,meta=backup_once();removed=retention(BACKUPS)
            status.update(status='completed',last_success_at=utc(),last_backup=folder.name,backup_seconds=meta['seconds'],removed=removed)
        except Exception as exc:status.update(status='failed',error_type=type(exc).__name__)
        status['cycle_seconds']=time.monotonic()-start
        next_start+=interval
        if next_start<time.monotonic():next_start=time.monotonic()+interval
        status['next_due_in_seconds']=max(0,next_start-time.monotonic())
        write_json(RESULTS/'scheduler_status.json',status);append(LOGS/'scheduler.log',status);print(json.dumps(status),flush=True);count+=1
        if cycles and count>=cycles:break
        time.sleep(max(0,next_start-time.monotonic()))

def wait_scheduler():
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        path=RESULTS/'scheduler_status.json'
        if path.exists():
            s=json.loads(path.read_text())
            if s.get('status')=='completed':
                age=(datetime.now(timezone.utc)-datetime.fromisoformat(s['last_success_at'])).total_seconds()
                manifest=BACKUPS/s['last_backup']/'manifest.json'
                if age<240 and manifest.exists() and s['configured_interval_seconds']==3600:
                    save('lab14_2_schedule.json',{'timestamp':utc(),'passed':True,'scheduler':s,'observed':'initial real scheduled backup completed; hourly interval configured, not a one-hour elapsed demonstration'});return
            if s.get('status')=='failed':raise RuntimeError('Scheduled backup failed; inspect logs/scheduler.log')
        time.sleep(2)
    raise RuntimeError('Scheduler did not complete a fresh initial backup in 180 seconds.')

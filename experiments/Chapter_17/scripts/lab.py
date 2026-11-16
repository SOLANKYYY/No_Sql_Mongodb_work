import json, os, time, statistics, uuid
from pathlib import Path
import numpy as np
from common import mongo, save, now, environment, ROOT, RESULTS, fingerprint
from logic import chunks, normalized, recall, make_prompt
EMBED_MODEL='sentence-transformers/all-MiniLM-L6-v2'
GEN_MODEL='google/flan-t5-small'
_embedder=None
_generator=None

def embed(texts):
    global _embedder
    if _embedder is None:
        from fastembed import TextEmbedding
        _embedder=TextEmbedding(model_name=EMBED_MODEL,cache_dir='/cache/fastembed',threads=2)
    return normalized(list(_embedder.embed(texts,batch_size=64)))

def generate(prompt):
    global _generator
    if _generator is None:
        import torch
        from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
        torch.set_num_threads(2)
        tok=AutoTokenizer.from_pretrained(GEN_MODEL)
        model=AutoModelForSeq2SeqLM.from_pretrained(GEN_MODEL).eval()
        _generator=(tok,model)
    tok,model=_generator
    inputs=tok(prompt,return_tensors='pt',truncation=False)
    if inputs['input_ids'].shape[1]>2048:
        raise ValueError('Prompt too long. Shorten question/history; no silent history truncation.')
    import torch
    with torch.inference_mode(): out=model.generate(**inputs,max_new_tokens=120,do_sample=False)
    return tok.decode(out[0],skip_special_tokens=True)

def ensure_index(col,name):
    from pymongo.operations import SearchIndexModel
    existing=list(col.list_search_indexes(name))
    if not existing:
        col.create_search_index(SearchIndexModel(name=name,type='vectorSearch',definition={
            'fields':[{'type':'vector','path':'embedding','numDimensions':384,'similarity':'cosine'}]}))
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        state=list(col.list_search_indexes(name))
        if state and state[0].get('status')=='FAILED': raise RuntimeError('Search index failed: '+name)
        if state and state[0].get('queryable'): return
        print('Waiting for vector index:',name,flush=True);time.sleep(5)
    raise TimeoutError('Vector search index not queryable within 10 minutes')

def retrieve(col,q,k=3):
    return list(col.aggregate([{'$vectorSearch':{'index':'rag_vector','path':'embedding','queryVector':q.tolist(),'numCandidates':60,'limit':k}},
        {'$project':{'text':1,'source':1,'score':{'$meta':'vectorSearchScore'}}}]))

def ask(question,session='interactive',db=None):
    own=db is None
    client=mongo() if own else None
    if own: db=client['exercise17']
    q=embed([question])[0]
    hits=retrieve(db.chunks,q)
    if len(hits)!=3: raise RuntimeError('Expected three indexed chunks; run RUN.ps1 first')
    history=list(db.conversations.find({'session':session},{'_id':0}).sort('created_ns',-1).limit(5))[::-1]
    prompt=make_prompt(question,hits,history)
    t=time.perf_counter();answer=generate(prompt);duration=time.perf_counter()-t
    entry={'session':session,'created_ns':time.time_ns(),'question':question,'answer':answer}
    db.conversations.insert_one(entry)
    result={'question':question,'answer':answer,'history_exchanges_used':len(history),'history_ids':[h['created_ns'] for h in history],
            'retrieved':[{'id':str(h['_id']),'source':h['source'],'text':h['text'],'score':h['score']} for h in hits],
            'prompt':prompt,'generation_seconds':duration,'model':GEN_MODEL}
    print(json.dumps(result,indent=2),flush=True)
    if own: client.close()
    return result

def prepare():
    print('Downloading real embedding and local generation models (cached after first use).',flush=True)
    embed(['MongoDB vector search'])
    generate('Question: What is a database? Answer:')

def benchmark(db):
    import faiss
    faiss.omp_set_num_threads(2)
    # Generated varied text, not Wikipedia and not real threat events.
    rng=np.random.default_rng(17)
    types=['phishing','ransomware','credential theft','botnet','malicious scanning','DNS tunneling','data exfiltration','software vulnerability']
    actions=['isolate affected hosts','rotate compromised credentials','validate source reputation','review authentication logs','check network indicators','patch vulnerable software','confirm analyst findings','correlate endpoint telemetry']
    texts=[f"Training case {i}: {rng.choice(types)} affects asset {rng.integers(1,1000)} in region {rng.integers(1,40)}. Analysts {rng.choice(actions)} and {rng.choice(actions)}. The confidence score is {rng.integers(10,100)} percent; evidence batch {rng.integers(1,10000)} requires review." for i in range(5000)]
    print('Embedding 5,000 generated text documents...',flush=True)
    x=embed(texts)
    db.benchmark.delete_many({})
    for start in range(0,5000,500):
        db.benchmark.insert_many([{'_id':i,'text':texts[i],'embedding':x[i].tolist()} for i in range(start,start+500)])
    queries=[f"Investigation {i}: How should a team respond to {rng.choice(types)} affecting region {rng.integers(1,40)} and {rng.choice(actions)}?" for i in range(100)]
    q=embed(queries)
    exact=faiss.IndexFlatIP(384);exact.add(x)
    _,truth=exact.search(q,20)
    rows=[]
    def measure(index,label,params,build):
        index.search(q[:3],20) # warm-up outside measured queries
        lat=[];recs=[]
        for vector,gt in zip(q,truth):
            t=time.perf_counter();_,ids=index.search(vector[None,:],20);lat.append((time.perf_counter()-t)*1000)
            recs.append(recall(ids[0],gt))
        row={'engine':'FAISS CPU','index':label,**params,'build_seconds':build,'mean_ms':statistics.mean(lat),'median_ms':statistics.median(lat),'recall_at_20':statistics.mean(recs),'queries':100}
        rows.append(row);print(json.dumps(row),flush=True)
    for ef in [32,64,128,256]:
        h=faiss.IndexHNSWFlat(384,16,faiss.METRIC_INNER_PRODUCT);h.hnsw.efConstruction=ef
        t=time.perf_counter();h.add(x);build=time.perf_counter()-t
        for search in [32,64,128]:
            h.hnsw.efSearch=search;measure(h,'HNSW',{'M':16,'efConstruction':ef,'efSearch':search},build)
    for nlist in [50,100]:
        ivf=faiss.IndexIVFFlat(faiss.IndexFlatIP(384),384,nlist,faiss.METRIC_INNER_PRODUCT)
        ivf.cp.seed=17
        t=time.perf_counter();ivf.train(x);ivf.add(x);build=time.perf_counter()-t
        for probe in [10,25,50,100]:
            if probe<=nlist:
                ivf.nprobe=probe;measure(ivf,'IVF',{'nlist':nlist,'nprobe':probe},build)
    # Separately measure the actual MongoDB HNSW-backed service against same exact ground truth.
    t=time.perf_counter();ensure_index(db.benchmark,'benchmark_vector');ready=time.perf_counter()-t
    deadline=time.monotonic()+600
    while True:
        count=list(db.benchmark.aggregate([{'$vectorSearch':{'index':'benchmark_vector','path':'embedding','queryVector':q[0].tolist(),'exact':True,'limit':5000}},{'$count':'n'}]))
        if count and count[0]['n']==5000: break
        if time.monotonic()>deadline: raise TimeoutError('Search index has not ingested all 5000 vectors')
        time.sleep(5)
    mongo_rows=[]
    for candidates in [100,400,1000]:
        lat=[];rec=[]
        for vector,gt in zip(q,truth):
            t=time.perf_counter()
            hits=list(db.benchmark.aggregate([{'$vectorSearch':{'index':'benchmark_vector','path':'embedding','queryVector':vector.tolist(),'numCandidates':candidates,'limit':20}},{'$project':{'_id':1}}]))
            lat.append((time.perf_counter()-t)*1000);rec.append(recall([h['_id'] for h in hits],gt))
        mongo_rows.append({'engine':'MongoDB $vectorSearch','numCandidates':candidates,'mean_ms':statistics.mean(lat),'median_ms':statistics.median(lat),'recall_at_20':statistics.mean(rec),'queries':100})
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    for kind in ['HNSW','IVF']:
        subset=[r for r in rows if r['index']==kind]
        plt.scatter([r['mean_ms'] for r in subset],[100*r['recall_at_20'] for r in subset],label=kind)
    plt.xlabel('Mean single-query latency (ms)');plt.ylabel('Recall@20 (%)');plt.legend();plt.title('FAISS CPU: 5,000 x 384, 100 queries');plt.tight_layout()
    RESULTS.mkdir(exist_ok=True,parents=True);plt.savefig(RESULTS/'latency_recall.png',dpi=160);plt.close()
    return {'documents':5000,'dimensions':384,'queries':100,'k':20,'corpus':'generated threat-training sentences; not Wikipedia or live events',
            'embedding_model':EMBED_MODEL,'corpus_sha256':fingerprint(texts),'rows':rows,'mongodb_rows':mongo_rows,
            'mongodb_index_ready_wait_seconds':ready,'scope':'FAISS HNSW vs IVF algorithm comparison; MongoDB HNSW service measured separately; no Atlas IVF claim',
            'ground_truth':'FAISS IndexFlatIP exact full scan on normalized embeddings; same corpus and queries'}

def run():
    save('run_state.json',{'status':'running','at':now()})
    client=mongo();db=client['exercise17']
    try:
        prepare()
        docs=json.loads((ROOT/'data/documents.json').read_text())
        records=[]
        for d in docs:
            for i,text in enumerate(chunks(d['text'])): records.append({'_id':d['id']+'-'+str(i),'source':d['title'],'text':text})
        vectors=embed([r['text'] for r in records])
        db.chunks.delete_many({})
        db.chunks.insert_many([{**r,'embedding':v.tolist()} for r,v in zip(records,vectors)])
        ensure_index(db.chunks,'rag_vector')
        for _ in range(120):
            if len(retrieve(db.chunks,vectors[0]))==3: break
            time.sleep(5)
        db.conversations.create_index([('session',1),('created_ns',-1)])
        session=str(uuid.uuid4())
        questions=['What is a false positive in threat intelligence?','How does source reputation help?','What is phishing?','What should we do about ransomware?','Why correlate independent evidence?','How can analysts reduce false positives?']
        turns=[ask(q,session,db) for q in questions]
        assert turns[-1]['history_exchanges_used']==5
        results=benchmark(db)
        evidence={'experiment':17,'passed':True,'at':now(),'environment':environment(),'database_version':client.server_info()['version'],
            'deployment':'MongoDB Atlas Local Docker; not hosted Atlas','documents':len(docs),'chunks':len(records),'rag':turns,'benchmark':results,
            'limitations':['Small local FLAN-T5 model can produce poor answers; review retrieved context and answers.','Atlas does not expose the screenshot IVF configuration; FAISS comparison is a documented adaptation.']}
        save('evidence.json',evidence);save('run_state.json',{'status':'passed','at':now()})
        print('EXERCISE 17 PASSED: real retrieval, local generation, five-exchange history, HNSW/IVF and MongoDB measurements.')
    finally: client.close()

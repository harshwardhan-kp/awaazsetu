"""Offline scoring of independently labelled results. Never contacts a provider."""
from __future__ import annotations
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics
import unicodedata

TYPES={'rescue','medical','water_in_home','road_waterlogging','other'}
BANDS={'critical','high','medium','low'}
LANGUAGES={'en','hi','mr'}


def ratio(n,d): return n/d if d else None


def words(text):
    if not isinstance(text,str): raise ValueError("Text fields must be strings")
    normalized=unicodedata.normalize('NFKC',text).casefold()
    # Preserve Indic combining marks; regex \w excludes those and corrupts words.
    return ''.join(' ' if unicodedata.category(c)[0] in ('P','S','C') else c for c in normalized).split()


def token_f1(reference,hypothesis):
    a,b=Counter(words(reference)),Counter(words(hypothesis))
    common=sum((a&b).values()); total=sum(a.values())+sum(b.values())
    return ratio(2*common,total)


def edit_distance(a,b):
    previous=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        current=[i]
        for j,y in enumerate(b,1):
            current.append(min(current[-1]+1,previous[j]+1,previous[j-1]+(x!=y)))
        previous=current
    return previous[-1]


def coordinates(value):
    if value is None: return None
    if not isinstance(value,(list,tuple)) or len(value)!=2: raise ValueError("Coordinates require [latitude, longitude]")
    lat,lon=value
    if not isinstance(lat,(int,float)) or not isinstance(lon,(int,float)) or isinstance(lat,bool) or isinstance(lon,bool): raise ValueError('Invalid coordinates')
    lat,lon=float(lat),float(lon)
    if not math.isfinite(lat+lon) or not -90<=lat<=90 or not -180<=lon<=180: raise ValueError('Invalid coordinates')
    return lat,lon


def distance(a,b):
    a,b=coordinates(a),coordinates(b)
    lat1,lon1,lat2,lon2=map(math.radians,[*a,*b])
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000*2*math.asin(math.sqrt(min(1,max(0,h))))


def pair_metrics(rows):
    tp=fp=fn=tn=0
    for row in rows:
        gold,pred=row['same_event'],row['predicted_same_event']
        if type(gold) is not bool or type(pred) is not bool: raise ValueError('Pair labels must be JSON booleans')
        tp+=gold and pred; fp+=not gold and pred; fn+=gold and not pred; tn+=not gold and not pred
    return {'samples':len(rows),'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':ratio(tp,tp+fp),'recall':ratio(tp,tp+fn),'f1':ratio(2*tp,2*tp+fp+fn),'gold_positive':tp+fn,'gold_negative':tn+fp}


def report_metrics(rows):
    correct=0; confusion=Counter(); phrases=[]; distances=[]; geo_gold=0; geo_missing=0; latencies=[]
    types=Counter(); bands=Counter(); predicted_bands=Counter(); languages=Counter()
    for row in rows:
        if row['language'] not in LANGUAGES: raise ValueError('Unsupported report language')
        languages[row['language']]+=1
        expected,predicted=row['expected'],row['predicted']
        if expected['incident_type'] not in TYPES or predicted['incident_type'] not in TYPES: raise ValueError('Invalid incident type')
        if expected['severity_band'] not in BANDS or predicted['severity_band'] not in BANDS: raise ValueError('Invalid severity band')
        types[expected['incident_type']]+=1; bands[expected['severity_band']]+=1; predicted_bands[predicted['severity_band']]+=1
        correct+=expected['incident_type']==predicted['incident_type']
        confusion[expected['severity_band'],predicted['severity_band']]+=1
        if expected.get('location_text') is not None:
            val=token_f1(expected['location_text'],predicted.get('location_text') or '')
            if val is not None: phrases.append(val)
        if expected.get('coordinates') is not None:
            geo_gold+=1; coordinates(expected['coordinates'])
            if predicted.get('coordinates') is None: geo_missing+=1
            else: distances.append(distance(expected['coordinates'],predicted['coordinates']))
        if row.get('latency_ms') is not None:
            latency=float(row['latency_ms'])
            if isinstance(row['latency_ms'],bool) or not math.isfinite(latency) or latency<0: raise ValueError('latency_ms must be finite and nonnegative')
            latencies.append(latency)
    per_class={}
    for label in sorted(set(bands)|set(predicted_bands)):
        tp=confusion[label,label]; fp=sum(n for (g,p),n in confusion.items() if p==label and g!=label); fn=sum(n for (g,p),n in confusion.items() if g==label and p!=label)
        per_class[label]={'gold_samples':bands[label],'predicted_samples':predicted_bands[label],'f1':ratio(2*tp,2*tp+fp+fn)}
    f1s=[x['f1'] for x in per_class.values() if x['f1'] is not None]
    return {'samples':len(rows),'incident_type_accuracy':ratio(correct,len(rows)),'incident_type_gold_coverage':dict(types),'severity_macro_f1':statistics.mean(f1s) if f1s else None,'severity_per_class':per_class,'severity_gold_coverage':dict(bands),'critical_recall':ratio(confusion['critical','critical'],bands['critical']),'language_samples':dict(languages),'location_phrase_token_f1':statistics.mean(phrases) if phrases else None,'location_phrase_samples':len(phrases),'location_gold_coordinate_samples':geo_gold,'location_missing_predictions':geo_missing,'location_within_500m':ratio(sum(d<=500 for d in distances),geo_gold),'location_measured_distance_samples':len(distances),'latency_median_ms':statistics.median(latencies) if latencies else None,'latency_samples':len(latencies)}


def voice_metrics(rows):
    grouped={}
    for row in rows:
        language=row['language']
        if language not in LANGUAGES: raise ValueError('Unsupported voice language')
        bucket=grouped.setdefault(language,{'samples':0,'reference_words':0,'word_edits':0,'empty_reference_samples':0})
        ref,hyp=words(row['reference']),words(row['transcript'])
        bucket['samples']+=1; bucket['reference_words']+=len(ref); bucket['word_edits']+=edit_distance(ref,hyp); bucket['empty_reference_samples']+=not ref
    for language in sorted(LANGUAGES):
        bucket=grouped.setdefault(language,{'samples':0,'reference_words':0,'word_edits':0,'empty_reference_samples':0})
        bucket['wer']=ratio(bucket['word_edits'],bucket['reference_words'])
    return grouped


def feedback_metrics(rows):
    assisted=[]; ratings=[]
    for row in rows:
        value=row.get('assisted','').strip().lower()
        if value:
            if value not in ('true','false','1','0','yes','no'): raise ValueError('Invalid assisted value')
            assisted.append(value in ('true','1','yes'))
        value=row.get('rating','').strip()
        if value:
            score=float(value)
            if not math.isfinite(score) or not 1<=score<=5: raise ValueError('Ratings must be between 1 and 5')
            ratings.append(score)
    return {'samples':len(rows),'assistance_samples':len(assisted),'assistance_rate':ratio(sum(assisted),len(assisted)),'rating_samples':len(ratings),'rating_mean':statistics.mean(ratings) if ratings else None,'rating_median':statistics.median(ratings) if ratings else None}


def read_jsonl(path):
    if not path: return []
    rows=[]; ids=set()
    for line_no,line in enumerate(Path(path).read_text(encoding='utf-8').splitlines(),1):
        if not line.strip(): continue
        try:
            row=json.loads(line)
            if not isinstance(row,dict) or not isinstance(row.get('id'),str) or not row['id'].strip(): raise ValueError('Each row requires a nonempty string id')
            if row['id'] in ids: raise ValueError('Duplicate id')
            ids.add(row['id']); rows.append(row)
        except (ValueError,TypeError) as exc: raise ValueError(f'{path}: line {line_no}: {exc}') from exc
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports',required=True,type=Path)
    parser.add_argument('--pairs',type=Path); parser.add_argument('--voice',type=Path); parser.add_argument('--feedback',type=Path)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        feedback=[]
        if args.feedback:
            with args.feedback.open(encoding='utf-8',newline='') as stream:
                reader=csv.DictReader(stream)
                if not {'assisted','rating'}.issubset(reader.fieldnames or []): raise ValueError('Feedback CSV requires assisted,rating headers')
                feedback=list(reader)
        result={'note':'User-supplied labels; quality and independence require human verification. Offline only. No metrics establish emergency readiness.','reports':report_metrics(read_jsonl(args.reports)),'duplicates':pair_metrics(read_jsonl(args.pairs)),'voice_by_language':voice_metrics(read_jsonl(args.voice)),'feedback':feedback_metrics(feedback)}
        output=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
        if args.output: args.output.write_text(output,encoding='utf-8')
        else: print(output,end='')
    except (ValueError,KeyError,TypeError,OSError) as exc:
        parser.error(str(exc))

if __name__=='__main__': main()

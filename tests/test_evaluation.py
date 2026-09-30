import json
import pytest
from scripts.evaluate_heldout import report_metrics,pair_metrics,voice_metrics,feedback_metrics,read_jsonl


def report(gold,pred,kind='rescue',pred_kind='rescue',**extra):
    return {'id':gold+pred,'language':'en','expected':{'incident_type':kind,'severity_band':gold},'predicted':{'incident_type':pred_kind,'severity_band':pred},**extra}


def test_independently_computed_classification_metrics():
    rows=[report('critical','critical'),report('critical','high',pred_kind='other'),report('high','high'),report('low','high')]
    result=report_metrics(rows)
    assert result['incident_type_accuracy']==.75
    assert result['critical_recall']==.5
    # critical F1=2/3; high F1=1/2; low F1=0 => macro=7/18.
    assert result['severity_macro_f1']==pytest.approx(7/18)
    assert result['severity_gold_coverage']=={'critical':2,'high':1,'low':1}


def test_duplicate_metrics_counts_and_zero_positive_denominator():
    rows=[{'same_event':a,'predicted_same_event':b} for a,b in [(True,True),(True,False),(False,True),(False,False)]]
    assert pair_metrics(rows)=={'samples':4,'tp':1,'fp':1,'fn':1,'tn':1,'precision':.5,'recall':.5,'f1':.5,'gold_positive':2,'gold_negative':2}
    assert pair_metrics([{'same_event':False,'predicted_same_event':False}])['f1'] is None
    with pytest.raises(ValueError): pair_metrics([{'same_event':1,'predicted_same_event':True}])


def test_location_missing_predictions_latency():
    a=report('high','high',latency_ms=100);b=report('low','low',latency_ms=700);c=report('low','low',latency_ms=300)
    a['expected'].update(location_text='Ekta Nagar school',coordinates=[18.478,73.819])
    a['predicted'].update(location_text='Ekta Nagar',coordinates=[18.479,73.819])
    b['expected'].update(location_text='Warje school',coordinates=[18.478,73.819])
    b['predicted'].update(location_text='',coordinates=[19.,74.])
    c['expected'].update(coordinates=[18.478,73.819])
    result=report_metrics([a,b,c])
    assert result['location_phrase_token_f1']==pytest.approx(.4) # .8 and 0 averaged
    assert result['location_within_500m']==pytest.approx(1/3) # missing is a failed prediction
    assert result['location_missing_predictions']==1
    assert result['latency_median_ms']==300


def test_wer_edits_by_language_and_empty_references():
    result=voice_metrics([{'language':'en','reference':'one two three','transcript':'one four three extra'},{'language':'mr','reference':'घरात पाणी आहे','transcript':'घरात पाणी'},{'language':'hi','reference':'','transcript':'extra'}])
    assert result['en']['wer']==pytest.approx(2/3)
    assert result['mr']['wer']==pytest.approx(1/3)
    assert result['hi']['wer'] is None and result['hi']['word_edits']==1


def test_feedback_counts_and_invalid_values():
    result=feedback_metrics([{'assisted':'yes','rating':'5'},{'assisted':'no','rating':'3'},{'assisted':'','rating':''}])
    assert result['samples']==3 and result['assistance_rate']==.5
    assert result['rating_mean']==4 and result['rating_samples']==2
    with pytest.raises(ValueError): feedback_metrics([{'rating':'NaN'}])


def test_empty_metrics_are_null_not_success():
    result=report_metrics([])
    assert result['samples']==0 and result['incident_type_accuracy'] is None
    assert result['critical_recall'] is None and result['severity_macro_f1'] is None
    assert result['location_within_500m'] is None
    assert feedback_metrics([])['assistance_rate'] is None
    assert voice_metrics([])['mr']['wer'] is None


def test_loader_rejects_duplicate_ids(tmp_path):
    path=tmp_path/'heldout.jsonl'
    path.write_text(json.dumps({'id':'a'})+'\n'+json.dumps({'id':'a'})+'\n')
    with pytest.raises(ValueError,match='Duplicate id'):read_jsonl(path)


def test_cli_offline_json_output(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    path=tmp_path/'empty.jsonl'; path.write_text('')
    command=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/evaluate_heldout.py'),'--reports',str(path)]
    process=subprocess.run(command,capture_output=True,text=True,check=True)
    result=json.loads(process.stdout)
    assert result['reports']['samples']==0 and result['reports']['severity_macro_f1'] is None
    assert result['voice_by_language']['hi']['samples']==0
    bad=tmp_path/'bad.csv';bad.write_text('unrelated\nvalue\n')
    process=subprocess.run(command+['--feedback',str(bad)],capture_output=True,text=True)
    assert process.returncode!=0 and 'requires assisted,rating headers' in process.stderr


def test_invalid_location_coordinates_rejected():
    row=report('high','high')
    row['expected']['coordinates']=[float('nan'),73.]
    with pytest.raises(ValueError,match='Invalid coordinates'):report_metrics([row])

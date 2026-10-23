"""Create private, unscored annotation manifests for up to fifty supplied images."""
import argparse
import json
import os
from pathlib import Path

EXTENSIONS={'.jpg','.jpeg','.png','.webp','.pdf'}


def create_manifest(inputs,destination,*,provenance):
    destination=Path(destination).expanduser().resolve()
    project=Path(__file__).resolve().parents[2]
    if destination.is_relative_to(project):raise ValueError('Keep annotations outside the checkout.')
    if destination.exists():raise FileExistsError('Existing ground truth will not be overwritten.')
    paths=[Path(path).expanduser().resolve() for path in inputs]
    if not 1<=len(paths)<=50 or len(paths)!=len(set(paths)):raise ValueError('Supply one to fifty distinct documents.')
    if provenance not in {'real_private','anonymized_real'}:raise ValueError('Declare the actual input provenance.')
    if any(not path.is_file() or path.suffix.lower() not in EXTENSIONS for path in paths):raise ValueError('Use existing supported document files.')
    documents=[{'id':f'R{index:03d}','path':str(path),'provenance':provenance,
        'category':None,'variant':'unreviewed','annotationStatus':'not_started',
        'groundTruth':{'complete':False,'annotationSource':'Pending independent manual annotation.','deadlines':[],'amounts':[]}}
        for index,path in enumerate(paths,1)]
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    with os.fdopen(os.open(destination,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w',encoding='utf-8') as file:
        json.dump({'schemaVersion':1,'datasetId':'private-manual-evaluation','documents':documents},file,ensure_ascii=False,indent=2);file.write('\n')
    destination.chmod(0o600)
    return len(documents)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True,type=Path);parser.add_argument('--provenance',choices=['real_private','anonymized_real'],required=True)
    parser.add_argument('inputs',nargs='+',type=Path);args=parser.parse_args()
    count=create_manifest(args.inputs,args.output,provenance=args.provenance)
    print(f'Created {count} private unannotated entries. Categorize and label them before evaluation; no accuracy was scored.')

#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timezone
from pathlib import Path

def parse_args():
    p=argparse.ArgumentParser()
    p.add_argument('--product', required=True)
    p.add_argument('--status', choices=['success','failure'], required=True)
    p.add_argument('--started-utc', required=True)
    p.add_argument('--runtime-seconds', type=int, required=True)
    p.add_argument('--schedule', required=True)
    p.add_argument('--outputs-json', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--message', default='')
    return p.parse_args()

def main():
    a=parse_args()
    payload={
      'schema_version': 1,
      'product': a.product,
      'status': a.status,
      'scheduled_event': os.getenv('GITHUB_EVENT_NAME') == 'schedule',
      'event_name': os.getenv('GITHUB_EVENT_NAME',''),
      'schedule_utc': a.schedule,
      'started_utc': a.started_utc,
      'completed_utc': datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),
      'runtime_seconds': a.runtime_seconds,
      'workflow_run_id': os.getenv('GITHUB_RUN_ID',''),
      'workflow_run_attempt': os.getenv('GITHUB_RUN_ATTEMPT',''),
      'workflow_url': f"{os.getenv('GITHUB_SERVER_URL','https://github.com')}/{os.getenv('GITHUB_REPOSITORY','')}/actions/runs/{os.getenv('GITHUB_RUN_ID','')}",
      'repository': os.getenv('GITHUB_REPOSITORY',''),
      'commit_sha': os.getenv('GITHUB_SHA',''),
      'branch': os.getenv('GITHUB_REF_NAME',''),
      'outputs': json.loads(a.outputs_json),
      'message': a.message,
    }
    out=Path(a.output); out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2)+'\n')
    print(json.dumps(payload, indent=2))
if __name__=='__main__': main()

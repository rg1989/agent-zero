import os
import json
import glob
import time
from pathlib import Path
from flask import Flask, jsonify, send_from_directory
from collections import defaultdict
from datetime import datetime

app = Flask(__name__, static_folder='static')
CHATS_DIR = '/a0/usr/chats'

def parse_chats():
    """Parse all chat.json files and return structured monitoring data."""
    contexts = []
    all_tool_counts = defaultdict(int)
    all_skill_counts = defaultdict(int)
    global_timeline = []

    chat_dirs = glob.glob(os.path.join(CHATS_DIR, '*'))
    
    for chat_dir in sorted(chat_dirs):
        chat_json = os.path.join(chat_dir, 'chat.json')
        if not os.path.exists(chat_json):
            continue
        
        try:
            with open(chat_json, 'r') as f:
                data = json.load(f)
        except Exception as e:
            continue
        
        chat_id = data.get('id', os.path.basename(chat_dir))
        chat_name = data.get('name', chat_id)
        chat_type = data.get('type', 'user')
        last_message = data.get('last_message', '')
        agents_data = data.get('agents', [])
        logs = data.get('log', {}).get('logs', [])
        
        # Parse logs for tool usage
        tool_counts = defaultdict(int)
        skill_counts = defaultdict(int)
        timeline = []
        agent_tool_map = defaultdict(list)  # agentno -> list of tools used
        
        for log in logs:
            kvps = log.get('kvps', {})
            tool_name = kvps.get('tool_name', '')
            agentno = log.get('agentno', 0)
            log_type = log.get('type', '')
            heading = log.get('heading', '')
            content = log.get('content', '')
            ts = log.get('timestamp', 0)
            
            if tool_name and tool_name not in ('', 'null'):
                tool_counts[tool_name] += 1
                all_tool_counts[tool_name] += 1
                agent_tool_map[agentno].append(tool_name)
                
                # Check if it's a skill tool
                if tool_name == 'skills_tool' or tool_name.startswith('skills_tool:'):
                    skill_arg = kvps.get('tool_args', {}).get('skill_name', '')
                    if skill_arg:
                        skill_counts[skill_arg] += 1
                        all_skill_counts[skill_arg] += 1
            
            # Build timeline entries for significant events
            if log_type in ('agent', 'user', 'util') and ts:
                entry = {
                    'ts': ts,
                    'time': datetime.fromtimestamp(ts).strftime('%H:%M:%S'),
                    'type': log_type,
                    'heading': heading,
                    'tool': tool_name,
                    'agentno': agentno,
                    'chat_id': chat_id,
                    'chat_name': chat_name,
                }
                timeline.append(entry)
                global_timeline.append(entry)
        
        # Build agent hierarchy
        agent_hierarchy = []
        for ag in agents_data:
            ag_num = ag.get('number', 0)
            ag_data = ag.get('data', {})
            iteration = ag_data.get('iteration_no', 0)
            agent_hierarchy.append({
                'number': ag_num,
                'iteration': iteration,
                'tools_used': agent_tool_map.get(ag_num, []),
                'tool_counts': dict(tool_counts),
            })
        
        # Determine if context is active (last message within 5 minutes)
        is_active = False
        if last_message:
            try:
                lm_time = datetime.fromisoformat(last_message.replace('Z', '+00:00'))
                age_seconds = time.time() - lm_time.timestamp()
                is_active = age_seconds < 300  # active if within 5 min
            except:
                pass
        
        contexts.append({
            'id': chat_id,
            'name': chat_name,
            'type': chat_type,
            'last_message': last_message,
            'is_active': is_active,
            'agent_count': len(agents_data),
            'agents': agent_hierarchy,
            'tool_counts': dict(tool_counts),
            'skill_counts': dict(skill_counts),
            'event_count': len(logs),
            'timeline': sorted(timeline, key=lambda x: x['ts'], reverse=True)[:20],
        })
    
    # Sort by last_message descending
    contexts.sort(key=lambda x: x.get('last_message', ''), reverse=True)
    
    # Sort global timeline
    global_timeline.sort(key=lambda x: x['ts'], reverse=True)
    
    return {
        'contexts': contexts,
        'global_tool_counts': dict(all_tool_counts),
        'global_skill_counts': dict(all_skill_counts),
        'global_timeline': global_timeline[:50],
        'timestamp': time.time(),
    }

@app.route('/')
@app.route('/agent-monitor/')
@app.route('/agent-monitor')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/api/state')
@app.route('/agent-monitor/api/state')
def api_state():
    try:
        data = parse_chats()
        return jsonify(data)
    except Exception as e:
        return jsonify({'error': str(e), 'timestamp': time.time()})

@app.route('/static/<path:filename>')
@app.route('/agent-monitor/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port, debug=False)

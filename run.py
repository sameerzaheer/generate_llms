from flask import Flask, render_template, request, jsonify
from app.crawler import create_llms
from app.alternatives import firecrawl_get
import uuid
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading

app = Flask(__name__)

# Initialize the scheduler
scheduler = BackgroundScheduler()
scheduler.start()

def run_scheduled_task(task_id):
    """Function to run a scheduled task"""
    global scheduled_tasks
    
    # Find the task
    task = None
    for t in scheduled_tasks:
        if t['task_id'] == task_id:
            task = t
            break
    
    if task:
        print(f"Running scheduled task: {task_id}")
        print(f"  Base URL: {task['base_url']}")
        print(f"  Time Created: {task['time_created']}")
        print(f"  Current Status: {task['last_status']}")
        print(f"  Last Run: {task['time_last_run']}")
        print("-" * 50)
        
        # Update the task's last run time and status
        task['time_last_run'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # For now, just print a simple result
        try:
            generated_llms = create_llms(task['base_url'])
            print(f"Created llms for {task['base_url']} at time {datetime.now()} with length {len(generated_llms)}")
            task['last_result'] = generated_llms
            task['last_status'] = 'completed'
        except Exception as e:
            print(f"Error creating llms for {task['base_url']}: {e} at time {datetime.now()}")
            task['last_result'] = f"Error: {e}"
            task['last_status'] = 'error'
    else:
        print(f"Task {task_id} not found!")

# Dummy data for scheduled tasks
scheduled_tasks = [
    {
        'task_id': 'task_001',
        'base_url': 'https://example.com',
        'time_created': '2024-01-15 10:30:00',
        'time_last_run': '2024-01-20 14:45:00',
        'last_status': 'completed',
        'last_result': '# Example llms.txt\n\nThis is a sample llms.txt file for testing purposes.\n\n## Allowed Models\n- GPT-4\n- Claude-3\n- Gemini\n\n## Disallowed Models\n- GPT-3.5\n- Older models\n\n## Rate Limits\n- 100 requests per hour\n- 1000 requests per day'
    }
]

# Schedule all existing tasks to run every 10 seconds
for task in scheduled_tasks:
    scheduler.add_job(
        func=run_scheduled_task,
        trigger=IntervalTrigger(seconds=150),
        args=[task['task_id']],
        id=f"job_{task['task_id']}",
        replace_existing=True
    )

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    url = request.json.get('url')
    schedule_updates = request.json.get('scheduleUpdates', False)
    avoid_substrings = request.json.get('avoidSubstrings', '')
    
    # Parse avoid substrings into a list (split by newlines and filter empty lines)
    avoid_list = [line.strip() for line in avoid_substrings.split('\n') if line.strip()]
    
    print(f"URL: {url}")
    print(f"Schedule updates: {schedule_updates}")
    print(f"Avoid substrings: {avoid_list}")
    
    # Simulate generated text (replace with actual logic)
    generated_llms = create_llms(url)
    firecrawl_llms = firecrawl_get(url)
    
    # Only create scheduled task if checkbox is checked
    if schedule_updates:
        # Create a new scheduled task
        task_id = str(uuid.uuid4())
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        new_task = {
            'task_id': task_id,
            'base_url': url,
            'time_created': current_time,
            'time_last_run': current_time,
            'last_status': 'completed',
            'last_result': generated_llms
        }
        
        # Add the task to the list
        scheduled_tasks.append(new_task)
        
        # Schedule the new task to run every 30 seconds
        scheduler.add_job(
            func=run_scheduled_task,
            trigger=IntervalTrigger(seconds=30),
            args=[task_id],
            id=f"job_{task_id}",
            replace_existing=True
        )
        
        print(f"Created new scheduled task: {task_id} for URL: {url}")
    else:
        print(f"Generated llms.txt for URL: {url} (no scheduling)")
    
    return jsonify({'output1': generated_llms, 'output2': firecrawl_llms})

@app.route('/scheduled-tasks')
def get_scheduled_tasks():
    """Return all scheduled tasks"""
    return jsonify(scheduled_tasks)

@app.route('/delete/<task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete a specific task by ID"""
    global scheduled_tasks
    
    # Find and remove the task
    for i, task in enumerate(scheduled_tasks):
        if task['task_id'] == task_id:
            deleted_task = scheduled_tasks.pop(i)
            
            # Remove the scheduled job
            job_id = f"job_{task_id}"
            try:
                scheduler.remove_job(job_id)
                print(f"Removed scheduled job: {job_id}")
            except Exception as e:
                print(f"Error removing job {job_id}: {e}")
            
            return jsonify({
                'success': True,
                'message': f'Task {task_id} deleted successfully',
                'deleted_task': deleted_task
            })
    
    # Task not found
    return jsonify({
        'success': False,
        'message': f'Task {task_id} not found'
    }), 404

if __name__ == '__main__':
    print("Starting Flask app with APScheduler...")
    print("Scheduled tasks will run every 10 seconds")
    print("Press Ctrl+C to stop")
    try:
        app.run(debug=True)
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        scheduler.shutdown()
        print("Scheduler stopped")

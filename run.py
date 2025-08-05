from flask import Flask, render_template, request, jsonify
from app.crawler import create_llms
from app.alternatives import firecrawl_get
import uuid
import os
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import threading

class ScheduledTask:
    def __init__(self, task_id, base_url, time_created=None, time_last_run=None, last_status='pending', last_result=None, 
                 avoid_url_substring_list=None, use_llm=False, llm_instructions='', new_url_hashmap=None, anything_changed=False, max_pages=20):
        self.task_id = task_id
        self.base_url = base_url
        self.time_created = time_created or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.time_last_run = time_last_run
        self.last_status = last_status
        self.last_result = last_result
        self.avoid_url_substring_list = avoid_url_substring_list or []
        self.use_llm = use_llm
        self.llm_instructions = llm_instructions
        self.new_url_hashmap = new_url_hashmap
        self.anything_changed = anything_changed
        self.max_pages = max_pages

    def to_dict(self):
        """Convert task to dictionary for JSON serialization"""
        return {
            'task_id': self.task_id,
            'base_url': self.base_url,
            'time_created': self.time_created,
            'time_last_run': self.time_last_run,
            'last_status': self.last_status,
            'last_result': self.last_result,
            'avoid_url_substring_list': self.avoid_url_substring_list,
            'use_llm': self.use_llm,
            'llm_instructions': self.llm_instructions,
            'new_url_hashmap': self.new_url_hashmap,
            'anything_changed': self.anything_changed,
            'max_pages': self.max_pages
        }
    
    def update_last_run(self, status='completed', content_updated=False, result=None):
        """Update the last run time and status"""
        self.time_last_run = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.last_status = status
        if content_updated and result is not None:
            self.last_result = result
    
    def run(self):
        """Execute the scheduled task"""
        print(f"Running scheduled task: {self.task_id}")
        print(f"  Base URL: {self.base_url}")
        print(f"  Avoid substrings: {self.avoid_url_substring_list}")
        print(f"  Use LLM: {self.use_llm}")
        print(f"  LLM Instructions: {self.llm_instructions}")
        print(f"  Time Created: {self.time_created}")
        print(f"  Current Status: {self.last_status}")
        print(f"  Last Run: {self.time_last_run}")
        print("-" * 50)
        
        try:
            generated_llms, generated_llms_llm, new_url_hashmap, anything_changed = create_llms(self.base_url, self.avoid_url_substring_list, self.use_llm, self.llm_instructions, self.new_url_hashmap, max_pages=self.max_pages)
            llms_to_save = generated_llms
            if generated_llms_llm:
                llms_to_save = generated_llms_llm
            print(f"Ran llms for {self.base_url} at time {datetime.now()} with length {len(generated_llms)} and anything_changed: {anything_changed}")
            self.update_last_run('completed', content_updated=anything_changed, result=llms_to_save)
        except Exception as e:
            print(f"Error creating llms for {self.base_url}: {e} at time {datetime.now()}")
            self.update_last_run('error', f"Error: {e}")

class TaskManager:
    def __init__(self):
        self.tasks = {}
        self.scheduler = BackgroundScheduler()
        self.scheduler.start()
    
    def add_task(self, task_id, base_url, trigger_interval_seconds, last_result=None, avoid_url_substring_list=None, use_llm=False, llm_instructions='', new_url_hashmap=None, anything_changed=False, max_pages=20):
        """Add a new task to the manager"""
        task = ScheduledTask(task_id, base_url, last_result=last_result, 
                           avoid_url_substring_list=avoid_url_substring_list, 
                           use_llm=use_llm, llm_instructions=llm_instructions,
                           new_url_hashmap=new_url_hashmap, anything_changed=anything_changed, max_pages=max_pages)
        self.tasks[task_id] = task
        
        # Schedule the task to run every X seconds
        self.scheduler.add_job(
            func=self._run_task_wrapper,
            trigger=IntervalTrigger(seconds=trigger_interval_seconds),
            args=[task_id],
            id=f"job_{task_id}",
            replace_existing=True
        )
        
        print(f"Created new scheduled task: {task_id} for URL: {base_url}")
        return task
    
    def remove_task(self, task_id):
        """Remove a task from the manager"""
        if task_id in self.tasks:
            # Remove from scheduler
            job_id = f"job_{task_id}"
            try:
                self.scheduler.remove_job(job_id)
                print(f"Removed scheduled job: {job_id}")
            except Exception as e:
                print(f"Error removing job {job_id}: {e}")
            
            # Remove from tasks dict
            task = self.tasks.pop(task_id)
            print(f"TASK DELETED: {task_id} for URL: {task.base_url}")
            return task
        return None
    
    def get_task(self, task_id):
        """Get a task by ID"""
        return self.tasks.get(task_id)
    
    def get_all_tasks(self):
        """Get all tasks as a list of dictionaries"""
        return [task.to_dict() for task in self.tasks.values()]
    
    def _run_task_wrapper(self, task_id):
        """Wrapper function to run a task (for scheduler compatibility)"""
        task = self.get_task(task_id)
        if task:
            task.run()
        else:
            print(f"Task {task_id} not found!")

# Initialize the task manager
task_manager = TaskManager()

# Add initial dummy task
# dummy_task = task_manager.add_task(
#     'task_001',
#     'https://example.com',
#     30,
#     '# Example llms.txt\n\nThis is a sample llms.txt file for testing purposes.\n\n## Allowed Models\n- GPT-4\n- Claude-3\n- Gemini\n\n## Disallowed Models\n- GPT-3.5\n- Older models\n\n## Rate Limits\n- 100 requests per hour\n- 1000 requests per day'
# )
# dummy_task.time_created = '2024-01-15 10:30:00'
# dummy_task.time_last_run = '2024-01-20 14:45:00'
# dummy_task.last_status = 'completed'

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate():
    url = request.json.get('url')
    schedule_updates = request.json.get('scheduleUpdates', False)
    avoid_substrings = request.json.get('avoidSubstrings', '')
    use_llm = request.json.get('useLLM', False)
    llm_instructions = request.json.get('llmInstructions', '')
    trigger_interval = request.json.get('triggerInterval', 70)
    max_pages = request.json.get('maxPages', 20)
    
    # Parse avoid substrings into a list (split by newlines and filter empty lines)
    avoid_list = [line.strip() for line in avoid_substrings.split('\n') if line.strip()]
    
    print(f"URL: {url}")
    print(f"Schedule updates: {schedule_updates}")
    print(f"Use LLM: {use_llm}")
    print(f"LLM Instructions: {llm_instructions}")
    print(f"Trigger interval: {trigger_interval} seconds")
    print(f"Max pages: {max_pages}")
    print(f"Avoid substrings: {avoid_list}")
    
    # Simulate generated text (replace with actual logic)
    generated_llms, generated_llms_llm, new_url_hashmap, anything_changed = create_llms(url, avoid_list, use_llm, llm_instructions, max_pages=max_pages)
    firecrawl_llms = firecrawl_get(url)
    
    # Only create scheduled task if checkbox is checked
    if schedule_updates:
        # Create a new scheduled task using the task manager
        task_id = str(uuid.uuid4())
        task_manager.add_task(task_id, url, trigger_interval, generated_llms, avoid_list, use_llm, llm_instructions, new_url_hashmap, anything_changed, max_pages)
        print(f"Generated llms.txt for URL: {url} and created scheduled task with {trigger_interval}s interval")
    else:
        print(f"Generated llms.txt for URL: {url} (no scheduling)")
    
    return jsonify({'output1': generated_llms, 'output2': firecrawl_llms, 'output3': generated_llms_llm})

@app.route('/scheduled-tasks')
def get_scheduled_tasks():
    """Return all scheduled tasks"""
    return jsonify(task_manager.get_all_tasks())

@app.route('/delete/<task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete a specific task by ID"""
    deleted_task = task_manager.remove_task(task_id)
    
    if deleted_task:
        return jsonify({
            'success': True,
            'message': f'Task {task_id} deleted successfully',
            'deleted_task': deleted_task.to_dict()
        })
    else:
        return jsonify({
            'success': False,
            'message': f'Task {task_id} not found'
        }), 404

if __name__ == '__main__':
    print("Press Ctrl+C to stop")
    try:
        app.run(debug=False, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    except KeyboardInterrupt:
        print("\nShutting down scheduler...")
        task_manager.scheduler.shutdown()
        print("Scheduler stopped")

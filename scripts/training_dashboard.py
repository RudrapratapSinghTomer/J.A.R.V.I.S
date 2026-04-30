from flask import Flask, render_template_string, request, send_from_directory, jsonify
import csv
import os
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).parent.parent
AUDIO_DIR = (BASE_DIR / "data/training_audio").resolve()
CSV_PATH = AUDIO_DIR / "dataset.csv"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>JARVIS Training Dashboard</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #1e1e2e; color: #cdd6f4; padding: 20px; }
        h1 { color: #89b4fa; }
        .card { background: #313244; padding: 15px; border-radius: 8px; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        .controls { display: flex; gap: 10px; align-items: center; margin-top: 10px; flex-wrap: wrap; }
        audio { height: 30px; }
        button { padding: 8px 12px; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; }
        .btn-correct { background: #a6e3a1; color: #11111b; }
        .btn-partial { background: #f9e2af; color: #11111b; }
        .btn-wrong { background: #f38ba8; color: #11111b; }
        .btn-save { background: #89b4fa; color: #11111b; }
        input[type="text"] { flex-grow: 1; padding: 8px; border-radius: 4px; border: 1px solid #45475a; background: #1e1e2e; color: #cdd6f4; min-width: 200px; }
        .status { margin-left: 10px; font-size: 0.9em; color: #a6e3a1; }
        .heard { font-size: 1.2em; font-weight: bold; margin-bottom: 5px; }
        .rating-group { display: flex; gap: 5px; border-left: 2px solid #45475a; padding-left: 10px; margin-left: 5px;}
    </style>
</head>
<body>
    <h1>JARVIS Audio Training Dataset</h1>
    <p>Review the captured audio. Rank the accuracy and provide the actual text you spoke.</p>
    
    <div id="entries">
        {% for row in rows %}
        <div class="card" id="card-{{ loop.index }}">
            <div class="heard">"{{ row[2] }}"</div>
            <div style="font-size: 0.8em; color: #a6adc8;">Time: {{ row[0] }}</div>
            
            <div class="controls">
                <audio controls src="/audio/{{ row[1] }}"></audio>
                <input type="text" id="truth-{{ loop.index }}" value="{{ row[4] }}" placeholder="Type exact words spoken here..." onkeypress="if(event.key === 'Enter') document.getElementById('save-{{ loop.index }}').click();">
                <button id="save-{{ loop.index }}" class="btn-save" onclick="updateEntry({{ loop.index }}, '{{ row[0] }}', '{{ row[3] }}')">💾 Save Text</button>
                
                <div class="rating-group">
                    <button class="btn-correct" onclick="updateEntry({{ loop.index }}, '{{ row[0] }}', 'Correct')">Correct</button>
                    <button class="btn-partial" onclick="updateEntry({{ loop.index }}, '{{ row[0] }}', 'Partial')">Partial</button>
                    <button class="btn-wrong" onclick="updateEntry({{ loop.index }}, '{{ row[0] }}', 'Wrong')">Wrong</button>
                </div>
                <span class="status" id="status-{{ loop.index }}">
                    {% if row[3] %} Rated: {{ row[3] }} {% endif %}
                </span>
            </div>
        </div>
        {% endfor %}
        {% if not rows %}
        <p>No audio data collected yet. Start speaking to JARVIS!</p>
        {% endif %}
    </div>

    <script>
        function updateEntry(index, timestamp, rating) {
            const truth = document.getElementById('truth-' + index).value;
            const statusSpan = document.getElementById('status-' + index);
            
            fetch('/update', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ timestamp: timestamp, rating: rating, truth: truth })
            })
            .then(response => response.json())
            .then(data => {
                if(data.success) {
                    statusSpan.textContent = "Saved" + (rating ? ": " + rating : "!");
                    statusSpan.style.color = "#a6e3a1";
                } else {
                    statusSpan.textContent = "Error saving";
                    statusSpan.style.color = "#f38ba8";
                }
            });
        }
    </script>
</body>
</html>
"""

def read_csv():
    if not CSV_PATH.exists():
        return []
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        rows = list(reader)
        if len(rows) > 0 and rows[0][0] == 'Timestamp':
            rows = rows[1:] # skip header
        # Return newest first
        return list(reversed(rows))

def write_csv(updated_rows):
    with open(CSV_PATH, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Timestamp', 'AudioFile', 'WhisperHeard', 'Rating', 'GroundTruth'])
        writer.writerows(updated_rows)

@app.route('/')
def index():
    rows = read_csv()
    return render_template_string(HTML_TEMPLATE, rows=rows)

@app.route('/audio/<filename>')
def get_audio(filename):
    return send_from_directory(AUDIO_DIR, filename)

@app.route('/update', methods=['POST'])
def update_entry():
    data = request.json
    timestamp = data.get('timestamp')
    rating = data.get('rating')
    truth = data.get('truth')
    
    # We must read in original order, update, and write back
    if not CSV_PATH.exists():
        return jsonify({'success': False})
        
    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        rows = list(csv.reader(f))
        
    header = rows[0]
    data_rows = rows[1:]
    
    updated = False
    for r in data_rows:
        if r[0] == timestamp:
            r[3] = rating
            r[4] = truth
            updated = True
            break
            
    if updated:
        write_csv(data_rows)
        return jsonify({'success': True})
    return jsonify({'success': False})

if __name__ == '__main__':
    print(f"Server starting on http://localhost:5000")
    print(f"Monitoring directory: {AUDIO_DIR}")
    app.run(host='0.0.0.0', port=5000, debug=False)

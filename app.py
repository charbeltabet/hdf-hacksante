from flask import Flask, render_template, request, jsonify
import pyautogui
import time

app = Flask(__name__)

# Disable PyAutoGUI fail-safe for smoother operation (optional)
# pyautogui.FAILSAFE = True  # Move mouse to corner to abort

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        data = request.get_json()
        text = data.get('text', '')
        x_ratio = float(data.get('x', 0.5))
        y_ratio = float(data.get('y', 0.5))

        # Validate ratios are between 0 and 1
        x_ratio = max(0, min(1, x_ratio))
        y_ratio = max(0, min(1, y_ratio))

        # Get screen size
        screen_width, screen_height = pyautogui.size()

        # Calculate actual pixel position
        x_pos = int(x_ratio * screen_width)
        y_pos = int(y_ratio * screen_height)

        # Small delay to allow user to switch windows if needed
        time.sleep(0.5)

        # Click at the position
        pyautogui.click(x_pos, y_pos)

        # Small delay before typing
        time.sleep(0.1)

        # Type the text
        if text:
            pyautogui.typewrite(text, interval=0.02)

        return jsonify({
            'success': True,
            'message': f'Clicked at ({x_pos}, {y_pos}) and typed text',
            'screen_size': {'width': screen_width, 'height': screen_height},
            'click_position': {'x': x_pos, 'y': y_pos}
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/intake', methods=['GET'])
def intake_route():
    return render_template('intake.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=7500)

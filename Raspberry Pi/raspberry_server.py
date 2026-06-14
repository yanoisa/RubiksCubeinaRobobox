import time, atexit
from flask import Flask, request, jsonify
import RPi.GPIO as GPIO

# GPIO Setup
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
sequence = [ [1,0,0,0], [1,1,0,0], [0,1,0,0], [0,1,1,0],
             [0,0,1,0], [0,0,1,1], [0,0,0,1], [1,0,0,1] ]

#Pin Combination of six motors and there belonging pins
R = [17,18,10,9]
W = [11,8,7,16]
G = [24,25,5,6]
Y = [23,14,15,22]
O = [12,20,19,26]
B = [13,21,27,4]
FACE_PINS = {'F':R,'R':G,'L':B,'U':Y,'D':W,'B':O}

# Kalibrations of the motors first and third number belong together
# second and fourth number belong together.
FACE_KALIBRATIONS = { 
    'F': [-160, 32, 200, -72],
    'R': [-192, 64, -448, 64],
    'L': [-184, 56, -440, 56],
    'U': [-160, 32, -416, 32],
    'D': [-160, 32, 196, -68],
    'B': [-192, 64, 168, -40]
}

def rotate_dict_values(face, side1, side2, side3, side4):
    #shift the values. for example F, R, B, L -> R,B,L,F
    face[side1], face[side2], face[side3], face[side4] = face[side4], face[side1], face[side2], face[side3]

#setup
for pins in FACE_PINS.values():
    for p in pins:
        GPIO.setup(p,GPIO.OUT)
        GPIO.output(p,0)
# after programm is done
def cleanup_gpio():
    GPIO.cleanup()
    atexit.register(cleanup_gpio)

# Moving of a specific Pinscombination to a specific Step
def move_motor(pins, steps, delay=0.001):
    seq = sequence if steps>0 else sequence[::-1]
    for _ in range(abs(steps)):
        for pattern in seq:
            for pin, val in zip(pins, pattern):
                GPIO.output(pin, val)
            time.sleep(delay)
    for pin in pins:
        GPIO.output(pin, 0)
# Setup Server
app = Flask(__name__)

@app.route('/trigger', methods=['POST'])
def trigger():
    # send from rubiks cube solver
    if request.is_json:
        data = request.get_json(silent=True)
    #usually not needed but important for debugging
    else:
        # else try form field
        import ast
        raw = request.form.get('move_sequence','')
        try:
           data = {'move_sequence': ast.literal_eval(raw)}
        except Exception:
           return jsonify(error="Could not parse moves from form"), 400
   # getting the move 
    moves = data.get('move_sequence')
    if not isinstance(moves, list) or not moves:
        return jsonify(error="'move_sequence' must be a non-empty list"), 400

    # execute
    for move in moves:
        #prints the moves
        app.logger.info(f"Move: {move}")
        if move == 'x':
            rotate_dict_values(FACE_PINS,'F', 'R', 'B', 'L')
            rotate_dict_values(FACE_KALIBRATIONS,'F', 'R', 'B', 'L')
        elif move == "x'":
            rotate_dict_values(FACE_PINS,'F', 'L', 'B', 'R')
            rotate_dict_values(FACE_KALIBRATIONS,'F', 'L', 'B', 'R')
        elif move == 'y':
            rotate_dict_values(FACE_PINS, 'F', 'U', 'B', 'D')
            rotate_dict_values(FACE_KALIBRATIONS, 'F', 'U', 'B', 'D')
        elif move == "y'":
            rotate_dict_values( FACE_PINS, 'F', 'D', 'B', 'U')
            rotate_dict_values( FACE_KALIBRATIONS, 'F', 'D', 'B', 'U')
        else:
            face = move[0]
            pins = FACE_PINS.get(face)
            steps_options = FACE_KALIBRATIONS.get(face)
            if not pins:
                app.logger.warning(f"Invalid face '{face}'")
                continue
            # inverse 90° step
            if "'" in move:
                steps = steps_options[2]
                steps2 = steps_options[3]
                print(steps)
                print(steps2)
            # normal 90° Step
            else:
                # steps overmoving
                steps = steps_options[0]
                print(steps)
                # steps back
                steps2 = steps_options[1]
                print(steps2)
            move_motor(pins, steps)
            move_motor(pins, steps2)
            
            time.sleep(0.5)

    return jsonify(status="done", executed=moves), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

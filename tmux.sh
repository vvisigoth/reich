#!/bin/bash

SESSION_NAME=$(basename "$PWD")
#SESSION_NAME=tester

SCRIPT1=reich.py
SCRIPT2=summarize.py

# Start a new tmux session named 'my_session'
#tmux new-session -d -s $SESSION_NAME
tmux new-session -d -s $SESSION_NAME

# Rename the first window and split it vertically
tmux rename-window -t $SESSION_NAME:0 'Main'
tmux send-keys -t $SESSION_NAME:0 "export OPENAI_API_KEY=$(cat key)" C-m
tmux send-keys -t $SESSION_NAME:0 "clear" C-m
tmux send-keys -t $SESSION_NAME:0 "python $SCRIPT1" C-m
tmux split-window -h -t $SESSION_NAME:0

# Split the new pane horizontally
tmux split-window -v -t $SESSION_NAME:0.1

# Create a second window and run the second script
tmux new-window -t $SESSION_NAME:1 -n 'Detail'
tmux send-keys -t $SESSION_NAME:1 "export OPENAI_API_KEY=$(cat key)" C-m
tmux send-keys -t $SESSION_NAME:1 "clear" C-m
tmux send-keys -t $SESSION_NAME:1 "python $SCRIPT2" C-m

# Attach to the session
tmux attach-session -t $SESSION_NAME


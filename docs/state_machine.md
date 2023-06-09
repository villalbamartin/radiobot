State machine for the main loop
===============================

The main loop of the bot is a state machine. State machines are very powerful,
but also very difficult to properly document. This document explains how the
machine works, and hopefully it will remain up to date forever.


Notation
--------
This diagram uses the Statechart notation. The main differences between a
Statechart and a regular state machine are:

  * Parallel execution: You can define sub-machines, "run" them in parallel,
    and whenever one of them generates an event it will be broadcasted to all
    other parallel machines.
  * An event can trigger another. For instance, the transition `eat/not_hungry`
    means that the machine moves from its current state when receiving the
    `eat` event and generates a `not hungry` event while doing so.
  * States with timeout: boxes marked with `-/\/\---` are states that you
    leave either because you received a specific event (as usual) or because
    an amount of time has passed (the `timeout` event). This is useful to
    model situations like "I give a .wav file to the speech-to-text system
    and I eventually get an output out of it".


Overview
--------
The system works in two possible modes, "dialog mode" (the states on the 
left) and "radio mode" (the states on the right).

In dialog mode you use push-to-talk, which is why we differentiate between
pressing the space key and releasing it. This generates a .wav file that is
sent to the speech-to-text system for transcription. Once the system is done
we add this utterance to the chat history, generate a prompt, and send it
to the LLM to generate a proper response. Once the LLM has generated a new
utterance we speak it out loud, at which point we go back at the beginning
and the loop starts again.

Radio mode is similar but with one critical difference: we can start
calculating the next utterance while the current one is being spoken.
This leads to the `think_and_say` state where both things are happening in
parallel. If the next utterance is ready before the previous one is spoken
out loud then all we can do is wait in the `slow_tongue` state until the
previous sentence is done. On the other hand, if the system is done "speaking"
before the LLM is done then we move back to the `thinking_radio` state and
wait. This interplay makes the code a bit more complex, including some extra
states (`clear_queue` and `finish_talking`) that must be visited before going
back to dialog mode to collect any missing generated texts that we need to
throw away.

For the purpose of this model the LLM, the speech-to-text system, and the
user are simple machines that oscillate between two states. The LLM, for
instance, remains idle until it receives a prompt, at which point it
will work for some time, eventually generate an event, and return to
its starting state.

Finally, the text-only mode is a smaller version of this diagram where
the `press_space`/`release_space` are just gone. This second diagram is not
detailed in this document, but I have faith that you can figure it out
yourself.

Diagram
-------
```
        +-------------+    release_r       +------------+                     
  *---->| idle_dialog |------------------->| idle_radio |                     
     +->|             |<-------------------|            |                     
     |  +-------------+  release_r ^       +------------+                     
     |         | press_space       |             | transcribed                
     |         V                   |             V                           
     |  +-------------+            |       +----------------+                
     |  |  recording  |            |    +--| thinking_radio |<--------------+
     |  +-------------+            |    |  +----------------+               |
     |         | release_space     |    |         | llm_uttered             |
     |         V                   |    |         V                         |
     |  +--------------+           |    |  +---------------+                |
     |  | transcribing |           |    +--| think_and_say |--------------->|
     |  +--------------+           |    |  +---------------+  done_speaking |
     |         | transcribed       |    |         | llm_uttered             |
     |         V                   |    |         V                         |
     |  +--------------+           |    |  +---------------+                |
     |  |   thinking   |           |    |  |  slow_tongue  |----------------+
     |  +--------------+           |    |  +---------------+  done_speaking  
     |         | llm_uttered       |    |                |
     |         V                   |    |                | 
     |  +--------------+           |    V release_r      V release_r
     |  |   speaking   |           |  +-------------+  +----------------+
     |  +--------------+           +--| clear_queue |  | finish_talking |
     |         |                   |  +-------------+  +----------------+
     +---------+                   |         | llm_uttered      | done_speaking
    done_speaking                  |         V                  |
                                   +----------------------------+

  *------------------------------------------------+
  | LLM                                            |
  |     +------+       transcribed       +-/\/\---+|
  | *-->| Idle |------------------------>| think  ||
  |     |      |<------------------------|        ||
  |     +------+   timeout/llm_uttered   +--------+|
  +------------------------------------------------+

  *------------------------------------------------+
  | User                                           |
  |     +------+     press_space         +-/\/\---+|
  | *-->| Idle |------------------------>| speak  ||
  |     |      |<------------------------|        ||
  |     +------+  timeout/release_space  +--------+|
  +------------------------------------------------+

  *------------------------------------------------+
  | speech-to-text                                 |
  |     +------+      release_space      +-/\/\---+|
  | *-->| Idle |------------------------>| work   ||
  |     |      |<------------------------|        ||
  |     +------+   timeout/transcribed   +--------+|
  +------------------------------------------------+

```

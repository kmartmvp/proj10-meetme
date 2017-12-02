# Project 10 - MeetMe

## Description
No registration web application that allows a user to choose a meeting time and send url to peers to provide their busy and available times from their Google Calendar.

## Notes for Graders
In this current iteration, the process works in this way:
(1) Upon running `make run` on CLI, navigate to localhost in browser. The initial route is to create a meeting.
(2) Upon choosing a meeting, append the given UUID to end of URL, ie `localhost:5000/<UUID>`.
(3) This is to be sent to peers - navigating here will allow you (and peers) to put in your calendar credentials and load available times to database.
(4) Currently, the final meeting time shows up on the second page - the one sent to peers. Wait a bit - it seems to run a bit slow when testing. Refresh to see updated if new available times added.

## Detail
Uses pymongo to store instances of each meeting, and create a URL that can be sent to peers to pull from their Google Calendar to determine busy and available times. Available times are stored in the database and therefore meeting state is preserved - peers can continue to add their available times via the index route.

## Running
Navigate to folder in which this was cloned. Use `make run` to install the requirements and run flask server. Requirements can be "uninstalled" from pyenv with `make veryclean`.

## Author
Michael Hagel

mhagel@uoregon.edu

## Thank You's
Starter code provided by: Michal Young
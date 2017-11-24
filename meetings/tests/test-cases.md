### Test Cases

# For Graders:
See Piazza question @276 to see professor's permission to use text file for writing tests cases (instead of using Nose).

# Selected Calendars
```javascipt
$(".col-md-4").each(function(){
          if($(this).css("background-color") == "rgb(142, 188, 229)") {
            selectedCals.push($(this).attr("id"));
            console.log($(this).attr("id"));
          }
        });
```
This snippet from `index.html` will log to console the IDs of selected calendars. To check if Jinja2 is submitting calendar IDs correctly, assert that the log contains all respective IDs in browser.

# Busy Times
(1) Choose dates from 11/13/17 to some arbitrary date at least 4 days in the future. See if recurring events land in "Busy Times" div more than once.

(2) Choose Thursday, 11/16/17. Make sure all day event is NOT included (should be non-blocking).

(3) Choose calendars Three Twenty Two and and 322 lab hours. Choose time from 12:30pm to 1:30pm on 11/14 to 11/16. Ensure both blocking events "Thing to do every 4 days" and "Thing to Do" are both accounted for in "Busy Times".
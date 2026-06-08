# Canvas-Grade-Calculator

This tool takes in an HTML file of a Canvas Grades page and reads the HTML to calculate your grades. This is useful for classes that update the grades page but keeps your overall grade hidden. You will no longer need to manually calculate your grade!

This currently does not account for cases where the lowest grade gets dropped.

If no weights are found on the HTML page, it will calculate your grade by taking the total points earned and dividing by the total points possible.

## Usage

1. download the HTML page for the class whose grades you wish to calculate
2. change directory to the folder containing calculate_grade.py
3. run the following in your command line: "python calculate_grade.py FILE_PATH"

if your HTML's file path is  "C:\Users\willi\OneDrive\Desktop\grades.html", you would run this in your command line:
    python calculate_grade.py "C:\Users\willi\OneDrive\Desktop\grades.html"

from flask import Flask, render_template, request, redirect, url_for, make_response, abort
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, Form, SelectField, SubmitField, BooleanField, FieldList, FormField, TimeField, RadioField
from wtforms.widgets import TextArea
from math import ceil
import os
from forms import ContactForm
from dotenv import load_dotenv, find_dotenv

try:
	# for internal server
	from urlparse import urlparse, urljoin
except:
	# for heroku hosting:
	from urllib.parse import urlparse, urljoin

app = Flask(__name__)

app.config['SECRET_KEY'] = os.urandom(24)

# Load the environment variables from the .env file
load_dotenv(find_dotenv())

# Get the value of the GOOGLE_VERIFICATION_TOKEN variable
google_verification_token = os.getenv("GOOGLE_VERIFICATION_TOKEN")

@app.errorhandler(404)
def page_not_found(e):
    title = 'Not Found'
    code = '404'
    message = "We can't seem to find the page you're looking for."
    return render_template('error.html', code = code, message = message, title = title), 404

@app.errorhandler(403)
def page_forbidden(e):
    title = 'Forbidden'
    code = '403'
    message = "You do not have access to this page."
    return render_template('error.html', code = code, message = message, title = title), 403

@app.errorhandler(500)
def internal_server_error(e):
    title = 'Internal Server Error'
    code = '500'
    message = "The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application."
    return render_template('error.html', code = code, message = message, title = title), 500

@app.route('/', methods=['GET', 'POST'])
def index():
	info = {}
	info["sections"] = [{"title":"Resume","id":"resume"},{"title":"About","id":"about"}]
	form = ContactForm()
	if request.method == 'POST':
		if form.validate():
			return render_template('index.html', info = info, post = 'yup', form = form)
	elif request.method == 'GET':
		return render_template('index.html', info = info, form = form)

@app.route('/about')
def about():
    return redirect('/#about')

@app.route('/resume')
def resume():
    return redirect('/#resume')

@app.route('/portfolio')
def portfolio():
    return redirect('/#portfolio')

@app.route('/google'+google_verification_token+'.html')
def google_site_verification():
    return render_template('google_site_verification.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
	return redirect("/#contact")

# web scraping to get most recent track & field times

from bs4 import BeautifulSoup
import requests

tf_url = "https://www.athletic.net/TrackAndField/Athlete.aspx?AID=12719238"
xc_url = "https://www.athletic.net/CrossCountry/Athlete.aspx?AID=12719238"

def if_contains(arr, event_name):
	for item in arr:
		if item["name"] == event_name:
			return True
	return False

@app.route('/athletics')
def athletics():
	events = []
	event_index = None
	event_link = None
	personal_record = None
	# track and field
	r  = requests.get(tf_url)
	data = r.text
	soup = BeautifulSoup(data)

	data = []
	all_times = []

	records = soup.find('div', attrs = {'uib-collapse':'seasonRecordsCollapsed'})
	for title in records.findAll('h5'):
		events.append({"name":title.text,"id":title.text.strip()})
	for table in records.findAll('table', attrs = {'class':'table table-sm histEvent'}):
		table_body = table.find('tbody')
		rows = table_body.find_all('tr')
		for row in rows:
			cols = row.find_all('td')
			all_times.append([])
			for element in cols:
				for a in element.findAll('a'):
					all_times[rows.index(row)].append(a["href"])
				all_times[rows.index(row)].append(element.text)
			cols = [ele.text.strip() for ele in cols]
			data.append([ele for ele in cols if ele])
	print("all times!!!")
	print(all_times)
	print("****")
	for item in data:
		if (if_contains(events,item[0])):
			if event_index:
				if personal_record:
					print("processing... "+str(personal_record))
					events[event_index]["link"] = event_link
					if personal_record["min"] > 0:
						events[event_index]["time"] = str(personal_record["min"])+":"+str(personal_record["sec"])
					elif "throw" in personal_record:
						if personal_record["throw"]:
							events[event_index]["time"] = personal_record["min"]+"' "+personal_record["sec"]
					else:
						events[event_index]["time"] = personal_record["sec"]
					print("just updated... "+str(events[event_index]["time"]))
			current_event = item[0]
			event_index = events.index({"name":item[0],"id":item[0].strip()})
			if len(item)==6 and "/result/" in item[6]:
				event_link = "https://www.athletic.net"+item[6]
			temp_pr = data[data.index([item[0]])+1][2]
			if ":" in temp_pr:
				min_val = int(temp_pr.split(":")[0])
				sec_val = float(''.join([c for c in str(temp_pr.split(":")[1]) if c in '1234567890.']))
				personal_record = {"min":min_val,"sec":sec_val}
			elif "'" in temp_pr:
				personal_record = {"throw":True,"min":int(temp_pr.split("'")[0]),"sec":float(''.join([c for c in str(temp_pr.split("'")[1]) if c in '1234567890.']))}
			else:
				personal_record = {"min":0,"sec":float(''.join([c for c in str(temp_pr) if c in '1234567890.']))}
			continue
		if ":" in item[2]:
			if len(item)==6 and "/result/" in item[6]:
				event_link = "https://www.athletic.net"+item[6]
			temp = float(str(''.join([c for c in str(item[2].split(":")[1]) if c in '1234567890.'])))
			item1 = 60*float(item[2].split(":")[0])+temp
			item2 = 60*personal_record["min"]+personal_record["sec"]
			if (60*float(item[2].split(":")[0])+temp < 60*personal_record["min"]+personal_record["sec"]):
				temp_pr = item[2]
				personal_record = {"min":int(temp_pr.split(":")[0]),"sec":float(''.join([c for c in str(temp_pr.split(":")[1]) if c in '1234567890.']))}
		elif "'" in temp_pr:
			if len(item)==6 and "/result/" in item[6]:
				event_link = "https://www.athletic.net"+item[6]
			if(float(item[2].split("'")[0])+12*float(''.join([c for c in str(item[2].split("'")[1]) if c in '1234567890.'])) > personal_record["min"]+12*personal_record["sec"]):
				temp_pr = item[2]
				personal_record = {"throw":True,"min":int(temp_pr.split("'")[0]),"sec":float(''.join([c for c in str(float(temp_pr.split("' ")[1])) if c in '1234567890.']))}
		else:
			if len(item)==6 and "/result/" in item[6]:
				event_link = "https://www.athletic.net"+item[6]
			temp = float(str(''.join([c for c in item[2] if c in '1234567890.'])))
			if(float(temp)<60*personal_record["min"]+personal_record["sec"]):
				personal_record = {"min":0,"sec":float(''.join([c for c in str(item[2]) if c in '1234567890.']))}
	print(events)
	events.append({'name': u'Shot Put - 4kg', 'id': u'Shot Put - 4kg'})
	if events.index({'name': u'Shot Put - 4kg', 'id': u'Shot Put - 4kg'}):
		events[events.index({'name': u'Shot Put - 4kg', 'id': u'Shot Put - 4kg'})] = {'name': u'Shot Put - 4kg', 'id': u'Shot Put - 4kg','time':"26' 1"}
	if events[0]["name"] == "100 Meters":
		events[0] = {'name': u'100 Meters', 'id': u'100 Meters', 'time':'13.55'}

	for this_event in events:
		if "link" in this_event:
			if this_event["link"]:
				this_event["meet"] = "<a href='"+this_event["link"]+"'>DETAILS</a>"
			else:
				this_event["meet"] = "<a href='https://www.athletic.net/TrackAndField/Athlete.aspx?AID=12719238'>DETAILS</a>"
		else:
			this_event["meet"] = "<a href='https://www.athletic.net/TrackAndField/Athlete.aspx?AID=12719238'>DETAILS</a>"
	return render_template('athletics.html', events = events)

@app.route('/chem-project')
def chem_project():
    return render_template('chem_project.html')

@app.route('/spring-2020-independent-study')
def independent_study_spring_2020():
    return render_template('etude_independante_2020.html')

@app.route('/lets-get-this-bread')
def lets_get_this_bread():
    return redirect("http://lets-get-this-bread.herokuapp.com")

@app.route('/incub8')
def incub8():
    return redirect("http://incub8.herokuapp.com")

@app.route('/sanfrancisgo')
def sanfrancisgo():
    return redirect("http://sanfrancisgo.herokuapp.com")

@app.route('/baking-club')
def baking_club():
    return redirect("http://uhsbakingclub.herokuapp.com")

@app.route('/diatribe-college-day')
def diatribe_college_day():
    return redirect("http://diatribe.org/college")

@app.route('/sitemap.xml', methods=['GET'])
def sitemap():
    """Generate sitemap.xml """
    pages = []
    # All pages registed with flask apps
    for rule in app.url_map.iter_rules():
        if "GET" in rule.methods and len(rule.arguments) == 0:
            pages.append(rule.rule)

    sitemap_xml = render_template('sitemap_template.xml', pages=pages)
    response = make_response(sitemap_xml)
    response.headers["Content-Type"] = "application/xml"

    # return response
    return render_template('sitemap_template.xml', pages=pages)


# To speed up loading
app.jinja_env.cache = {}


if __name__ == "__main__":
	app.run(debug=False)
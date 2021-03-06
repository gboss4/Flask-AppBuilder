Introdution
===========

The main goal for this project is to provide a simple development framework that handles the main problems any web application or site encounters.

This will lower errors, bugs, project's time to deliver. It's intended to be a rapid application development tool.

Includes
--------

  - Security
    - Auto permissions lookup, based on exposed methods. It will grant all permissions to the Admin Role.
    - Inserts on the Database all the detailed permissions possible on your application.
    - Public (no authentication needed) and Private permissions.
    - Role based permissions.
    - Authentication based on OpenID and Database (Planning LDAP).
  - Views and Widgets
	- Auto menu generator.
	- Various view widgets: lists, master-detail, list of thumbnails etc
	- Select2, Datepicker, DateTimePicker
	- Menu with icons
	- Google charts with automatic group by.
  - Forms
	- Auto Create, Remove, Add, Edit and Show from Database Models
	- Labels and descriptions for each field
	- Image and File support for upload and database field association. It will handle everything for you.
	- Field sets for Form's (Django style).
  - i18n
	- Support for multi-language via Babel (still not working in package form)
  - Bootstrap 3.0.0 CSS and js, with Select2 and DatePicker




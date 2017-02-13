Welcome to Instagram Analysis
===================
Under development

Available pages:



Framework
---------

Python 2.7.9
Celery + redis
sqLite

Initial setup
------------------------
    
    $ pip install -r requirements
    $ python manage.py runserver


Development
------------------------

Execute the following commands to simulate the production environment

	$ python manage.py runserver
	$ redis-server  # Launch redis server for Celery
	$ celery -A master worker -l debug
	$ celery -A master beat -l debug

You can execute the following bash script to run redis, celery and celertbeat in
development environment:

	$ bash dev-processes.sh

Kill all celery workers, celerybeat and redis server with the following command

    $ ps auxww | grep 'celery' | grep 'worker' | awk '{print $2}' | xargs kill -9 && ps auxww | grep 'celery' | grep 'beat' | awk '{print $2}' | xargs kill -9 && ps auxww | grep 'redis-server' | awk '{print $2}' | xargs kill -9

Deployment on production
------------------------

Deployment made with Fabric. The production server runs the code under the
stable branch. master contains modifications pending to be uploaded to production
and that are available in the staging server. Use a branch to implement new
features.

1. Installing in remote server. Fresh installation.

    fab install  # Installs virtualenv, pip, supervisor, memcached in server
    fab create  # Creates virtualenv, clones repository, creates database
    fab deploy  # Deploys the code running in stable branch in server
    fab deploy:'branchname'  # Deploys an specific branch in production
    
When deploying to production using fab deploy task, the script will only ask
for the username and password of an account in github. The account used to
do the checkout shall have read permission on the project's repository.

Create matrix of spots per city
-------------------------------
    
    $ python manage.py create_matrix_spots


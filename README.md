Restaurant Menu App
======
This is an app to display all details of restaurants and menus in the database.

##Requirement
Please make sure you have the following components installed.
* [Vagrant](https://www.vagrantup.com/downloads.html)
* [VirtualBox](https://www.virtualbox.org/wiki/Downloads)

##Quickstart
Have your database prepared.
1. Run `vagrant ssh` to ssh to your linux environment in command line
2. run `python database_setup.py` and `python lotsofmenus.py` to setup database
3. Run `python FinalProject.py` and open localhost:5000/login to login to the app

##What you can do

###After login
1. You can see the restaurant list
2. Click on the menu button after the restaurant name, you can see the menu of each restaurant
3. Click on the edit button after the restaurant name, you can edit the restaurant info to the database
4. Click on the create new restaurant button, you can create a new restaurant to the database
5. Click on the delete button, you can delete the restaurant you choose
6. When you are in the menu list, you can click on edit button to edit each menu item.
7. In the menu list, you can click on delete button to delete each menu item.
8. In the menu list, you can click on create new menu item to create a new menu item.
9. There is always a cancel button to return to the last page

If you are not login, you can only view the restaurant and menu list.


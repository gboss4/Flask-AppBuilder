from flask import current_app, g, request, current_app
from flask.ext.appbuilder import Base
from flask.ext.login import current_user
from models import User, Role, PermissionView, Permission, ViewMenu, \
    assoc_permissionview_role
from sqlalchemy import MetaData, Table
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.ext.declarative import declarative_base
from werkzeug.security import generate_password_hash, check_password_hash



class SecurityManager(object):

    session = None
    auth_type = 1
    auth_role_admin = ""
    auth_role_public = ""
    lm = None
    oid = None

    def __init__(self, app, session):
        """
            SecurityManager contructor
            param app:
                The Flask app object
            param session:
                the database session for security tables, passed to BaseApp
        """
        self.session = session
        self.auth_type = self._get_auth_type(app)
        self.auth_role_admin = self._get_auth_role_admin(app)
        self.auth_role_public = self._get_auth_role_public(app)
                    
        self.lm = LoginManager(app)
        self.lm.login_view = 'login'
        self.oid = OpenID(app)
        self.lm.user_loader(self.load_user)        
        self.init_db()
        
    def load_user(self, pk):
        return self.get_user_by_id(int(pk))

    def before_request(self):
        g.user = current_user

    def migrate_get_new_obj(self, old_obj, new_obj):
        for col in old_obj.keys():
            setattr(new_obj,col,getattr(old_obj,col))
        return new_obj
        
    def migrate_obj(self, old_table, new_class):
        old_objs = self.session.query(old_table).all()
        for old_obj in old_objs:
            new_obj = self.migrate_get_new_obj(old_obj, new_class())
            self.session.add(new_obj)
            self.session.commit()
       
    def quick_mapper(self, table):
        Base = declarative_base()
        class GenericMapper(Base):
            __table__ = table
        return GenericMapper
            
       
    def migrate_db(self):
        """
            Migrate security tables from Flask-AppBuilder 0.2.X to 0.3.X
        """
        engine = self.session.get_bind(mapper=None, clause=None)
        inspector = Inspector.from_engine(engine)
        if 'user' in inspector.get_table_names() and 'role' in inspector.get_table_names() and 'permission' in inspector.get_table_names():
            
            print "Found previous security tables, migrating..."
            
            metadata = MetaData(engine)

            old_user = Table('user', metadata, autoload=True) 
            old_role = Table('role', metadata, autoload=True)
            old_permission = Table('permission', metadata, autoload=True)
            old_permission_view = Table('permission_view', metadata, autoload=True)
            old_view_menu = Table('view_menu', metadata, autoload=True)
            old_permission_view_role = Table('permission_view_role', metadata, autoload=True)
                        
            print "Migrating Views and Menus"
            self.migrate_obj(old_view_menu, ViewMenu)            
                        
            print "Migrating Permissions"
            self.migrate_obj(old_permission, Permission)
                
            print "Migrating Permissions on Views"
            self.migrate_obj(old_permission_view, PermissionView)
                                    
            print "Migrating Roles"
            self.migrate_obj(old_role, Role)
            
            print "Migrating Roles to Permissions on Views"
            self.migrate_obj(old_permission_view_role, self.quick_mapper(assoc_permissionview_role))            
            
            print "Migrating Users"
            self.migrate_obj(old_user, User)
            
                        
    def init_db(self):
        engine = self.session.get_bind(mapper=None, clause=None)        
        
        inspector = Inspector.from_engine(engine)
        if 'ab_user' not in inspector.get_table_names():
            print "Security DB not found Creating..."
            Base.metadata.create_all(engine)
            print "Security DB Created"
            self.migrate_db()
        if self.session.query(Role).filter_by(name = self.auth_role_admin).first() is None:
            role = Role()
            role.name = self.auth_role_admin
            self.session.add(role)
            self.session.commit()
            print "Inserted Role for public access", self.auth_role_admin            
        if not self.session.query(Role).filter_by(name = self.auth_role_public).first():
            role = Role()
            role.name = self.auth_role_public
            self.session.add(role)
            self.session.commit()
            print "Inserted Role for public access", self.auth_role_public
        if not self.session.query(User).all():
            user = User()
            user.first_name = 'Admin'
            user.last_name = 'User'
            user.username = 'admin'
            user.password = 'general'
            user.active = True
            user.role = self.session.query(Role).filter_by(name = self.auth_role_admin).first()
            self.session.add(user)
            self.session.commit()
            print "Inserted initial Admin user"
            print "Login using Admin/general"
        
        
  
    def auth_user_db(self, username, password):
        if username is None or username == "":
            return None
        user = self.session.query(User).filter_by(username = username, password = password).first()
        if user is None or (not user.is_active()):
            return None
        else:
            return user
    
    def auth_user_oid(self, email):
        user = self.session.query(User).filter_by(email = email).first()
        if user is None or (not user.is_active()):
            return None
        else:
            return user
  
    def reset_password(self, userid, password):
        user = self.get_user_by_id(userid)
        user.password = password
        self.session.commit()
    
    def get_user_by_id(self, pk):
        return self.session.query(User).get(pk)
  
  
    def _get_auth_type(self, app):
        if 'AUTH_TYPE' in self.app.config:
            return app.config['AUTH_TYPE']
        else:
            return AUTH_DB
      
    def _get_auth_role_admin(self, app):
        if 'AUTH_ROLE_ADMIN' in self.app.config:
            return app.config['AUTH_ROLE_ADMIN']
        else:
            return 'Admin'
      
    def _get_auth_role_public(self, app):
        """
            To retrive the name of the public role
        """
        if 'AUTH_ROLE_PUBLIC' in self.app.config:
            return app.config['AUTH_ROLE_PUBLIC']
        else:
            return 'Public'
  
    
    def is_menu_public(self, item):
        """
            Check if menu item has public permissions
    
            param item:
                menu item
        """
        role = self.session.query(Role).filter_by(name = self.auth_role_public).first()
        lst = role.permissions
        if lst:
            for i in lst:
                if item == i.view_menu.name:
                    return  True
            return False
        else: return False

    def is_item_public(self, permission_name, view_name):
        """
            Check if view has public permissions
    
            param permission_name:
                the permission: can_show, can_edit...
            param view_name:
                the name of the class view (child of BaseView)
        """

        role = self.session.query(Role).filter_by(name = self.auth_role_public).first()
        lst = role.permissions
        if lst:
            for i in lst:
                if (view_name == i.view_menu.name) and (permission_name == i.permission.name):
                    return True
            return False
        else: return False
        
    def has_menu_access(self, user, menu_name):
        
        lst = user.role.permissions
        if lst:
            for i in lst:
                if menu_name == i.view_menu.name:
                    return  True
            return False
        else: return False

    def has_permission_on_view(self, user, permission_name, view_name):
        lst = user.role.permissions
        if lst:
            for i in lst:
                if (view_name == i.view_menu.name) and (permission_name == i.permission.name):
                    return True
            return False
        else: return False
    
    def _add_permission(self, name):
        """
            Adds a permission to the backend
            param name:
                name of the permission to add: 'can_add','can_edit' etc...
        """
        perm = self.session.query(Permission).filter_by(name = name).first()
        if perm == None:
            perm = Permission()
            perm.name = name
            self.session.add(perm)
            self.session.commit()
            return perm
        return perm
        
        
    def _add_view_menu(self, name):
        """
            Adds a view menu to the backend
            param name:
                name of the view menu to add
        """
        view_menu = self.session.query(ViewMenu).filter_by(name = name).first()
        if view_menu == None:
            view_menu = ViewMenu()
            view_menu.name = name
            self.session.add(view_menu)
            self.session.commit()
            return view_menu
        return view_menu

    def _add_permission_view_menu(self, permission_name, view_menu_name):
        """
            Adds a permission on a view menu to the backend
            param permission_name:
                name of the permission to add: 'can_add','can_edit' etc...
            param view_menu_name:
                name of the view menu to add
        """
        vm = self._add_view_menu(view_menu_name)
        perm = self._add_permission(permission_name)
        pv = PermissionView()
        pv.view_menu_id, pv.permission_id = vm.id, perm.id
        self.session.add(pv)
        self.session.commit()
        print "Added Permission View" , str(pv)
        return pv
    
    
    def _find_permission(self, lst, item):
        for i in lst:
            if i.permission.name == item:
                return True
        return False
    
    def add_permissions_view(self, base_permissions, view_menu):
        """
            Adds a permission on a view menu to the backend
            param base_permissions:
                list of permissions from view (all exposed methods): 'can_add','can_edit' etc...
            param view_menu:
                name of the view or menu to add
        """
        view_menu_db = self.session.query(ViewMenu).filter_by(name = view_menu).first()
        if view_menu_db == None:
            view_menu_db = self._add_view_menu(view_menu)
        lst = self.session.query(PermissionView).filter_by(view_menu_id = view_menu_db.id).all()
        # No permissions for this view
        if lst == []:
            for permission in base_permissions:
                pv = self._add_permission_view_menu(permission, view_menu)
                role_admin = self.session.query(Role).filter_by(name = self.auth_role_admin).first()
                self.add_permission_role(role_admin, pv)
        else:
            for permission in base_permissions:
                if not self._find_permission(lst, permission):
                    pv = self._add_permission_view_menu(permission, view_menu)
                    role_admin = self.session.query(Role).filter_by(name = self.auth_role_admin).first()
                    self.add_permission_role(role_admin, pv)
            for item in lst:
                if item.permission.name not in base_permissions:
                    # perm to delete
                    pass

    def add_permissions_menu(self, view_menu):
        view_menu_db = self.session.query(ViewMenu).filter_by(name = view_menu).first()
        if view_menu_db == None:
            view_menu_db = self._add_view_menu(view_menu)
        lst = self.session.query(PermissionView).filter_by(view_menu_id = view_menu_db.id).all()
        if lst == []:
            pv = self._add_permission_view_menu('menu_access', view_menu)
            role_admin = self.session.query(Role).filter_by(name = self.auth_role_admin).first()
            self.add_permission_role(role_admin, pv)

    
    def add_permission_role(self, role, perm_view):
        if perm_view not in role.permissions:
            role.permissions.append(perm_view)
            self.session.merge(role)
            self.session.commit()
            print "Added Permission" , str(perm_view) , " to Role " , role.name

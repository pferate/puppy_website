from datetime import datetime
import hashlib
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from werkzeug.security import generate_password_hash, check_password_hash
from flask import current_app, request
from flask.ext.login import UserMixin, AnonymousUserMixin
from . import db, login_manager
from sqlalchemy.schema import UniqueConstraint


def initialize_database():
    users = {
        'admin@puppy': ('System', 'Administrator',
                        'pbkdf2:sha1:1000$kfiXB8ye$bc6035d7bb15c6005a5b322314751238d1c9e0c5', True),
        'pat@puppy': ('Pat', 'Ferate',
                      'pbkdf2:sha1:1000$kfiXB8ye$bc6035d7bb15c6005a5b322314751238d1c9e0c5', True),
    }
    groups = {
        'User': ('Basic user group', True),
        'Moderator': ('Moderator group', True),
        'Administrator': ('System administrator group', True),
    }

    for u in users:
        user = User.query.filter_by(email=u).first()
        if user is None:
            user = User(email=u)
        user.first_name = users[u][0]
        user.last_name = users[u][1]
        user.password_hash = users[u][2]
        db.session.add(user)

    for g in groups:
        group = Group.query.filter_by(name=g).first()
        if group is None:
            group = Group(name=g)
        group.description = groups[g][0]
        group.default = groups[g][1]
        db.session.add(group)

    admin_user = User.query.filter_by(email='admin@puppy').first()
    pat_user = User.query.filter_by(email='pat@puppy').first()

    admin_group = Group.query.filter_by(name='Administrator').first()
    user_group = Group.query.filter_by(name='User').first()

    admin_group.users.append(admin_user)
    db.session.add(admin_group)

    user_group.users.append(pat_user)
    db.session.add(user_group)

    db.session.commit()


class Notification(db.Model):
    __tablename__ = 'notifications'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text())
    message = db.Column(db.Text())
    read_on = db.Column(db.DateTime(), nullable=True)
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by_user = db.relationship("User",
                                      foreign_keys=created_by,
                                      backref=db.backref('created_by_user', lazy='dynamic'))
    sent_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    sent_to_user = db.relationship("User",
                                   foreign_keys=sent_to,
                                   backref=db.backref('sent_to_user', lazy='dynamic'))

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.__str__()

    def to_json(self):
        json_notifications = {
            'id': self.id,
            'title': self.title,
            'message': self.message,
            'created_on': str(self.created_on),
            'created_by': self.created_by_user.to_json(),
            'sent_to': self.sent_to_user.to_json(),
            'read_on': self.read_on
        }
        return json_notifications

    @staticmethod
    def bulk_notify(title, message, current_user_id):
        users = User.query.all()
        for user in users:
            notification = Notification()
            notification.title = title
            notification.message = message
            notification.created_by = current_user_id
            notification.sent_to = user.id
            db.session.add(notification)
        db.session.commit()

    def mark_read(self):
        self.read_on = datetime.utcnow()
        return self

company_resources = db.Table('company_resource',
                             db.Column('id', db.Integer, primary_key=True),
                             db.Column('company_id', db.Integer, db.ForeignKey('company.id')),
                             db.Column('resource_id', db.Integer, db.ForeignKey('resource.id')),
                             UniqueConstraint('company_id', 'resource_id')
                             )


class VentureResource(db.Model):
    __tablename__ = 'venture_resources'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    venture_id = db.Column('venture_id', db.Integer, db.ForeignKey('ventures.id'))
    company_id = db.Column('company_id', db.Integer, db.ForeignKey('company.id'))
    resource_id = db.Column('resource_id', db.Integer, db.ForeignKey('resource.id'))
    company = db.relationship("Company", foreign_keys=company_id)
    resource = db.relationship("Resource", foreign_keys=resource_id)

    @property
    def name(self):
        return '{} provided by {}'.format(self.resource.name, self.company.name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class VentureSkill(db.Model):
    __tablename__ = 'venture_user_skills'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    venture_id = db.Column('venture_id', db.Integer, db.ForeignKey('ventures.id'))
    user_id = db.Column('user_id', db.Integer, db.ForeignKey('users.id'))
    skill_id = db.Column('skill_id', db.Integer, db.ForeignKey('skills.id'))
    user = db.relationship("User", foreign_keys=user_id)
    skill = db.relationship("Skill", foreign_keys=skill_id)

    @property
    def name(self):
        return '{} provided by {}'.format(self.skill.name, self.user.display_name)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class Venture(db.Model):
    __tablename__ = 'ventures'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())
    description = db.Column(db.Text())
    public_info = db.Column(db.Text())
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by_user = db.relationship("User", foreign_keys=created_by)
    approved_on = db.Column(db.DateTime())
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_user = db.relationship("User", foreign_keys=approved_by)
    student_venture = db.Column(db.Boolean, default=True)
    alumni_venture = db.Column(db.Boolean, default=False)
    external_venture = db.Column(db.Boolean, default=False)
    resources = db.relationship('VentureResource', backref='venture', lazy='dynamic')
    skills = db.relationship('VentureSkill', backref='venture', lazy='dynamic')

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class Company(db.Model):
    __tablename__ = 'company'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())
    description = db.Column(db.Text())
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by_user = db.relationship("User", foreign_keys=created_by)
    approved_on = db.Column(db.DateTime())
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_user = db.relationship("User", foreign_keys=approved_by)
    resources = db.relationship('Resource', secondary=company_resources, backref=db.backref('company', lazy='dynamic'))

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class Resource(db.Model):
    __tablename__ = 'resource'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())
    description = db.Column(db.Text())
    created_on = db.Column(db.DateTime(), default=datetime.utcnow)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by_user = db.relationship("User", foreign_keys=created_by)
    approved_on = db.Column(db.DateTime())
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_user = db.relationship("User", foreign_keys=approved_by)

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


class Type(db.Model):
    __tablename__ = 'types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text())

    def __str__(self):
        return self.message

    def __repr__(self):
        return self.__str__()


class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(64))
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)
    parent = db.relationship('Category', remote_side=id, backref='children')
    # skills = db.relationship('Skill', backref='category', lazy='dynamic')

    def __str__(self):
        lineage = [self.name]
        next_parent = self.parent
        while next_parent:
            lineage.append(next_parent.name)
            next_parent = next_parent.parent
        lineage.reverse()
        return ' > '.join(lineage)

    def __repr__(self):
        return self.__str__()


skills_category = db.Table('skill_category',
                           db.Column('category_id', db.Integer, db.ForeignKey('categories.id')),
                           db.Column('skill_id', db.Integer, db.ForeignKey('skills.id')),
                           )


user_skills = db.Table('user_skill',
                       db.Column('id', db.Integer, primary_key=True),
                       db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                       db.Column('skill_id', db.Integer, db.ForeignKey('skills.id')),
                       UniqueConstraint('user_id', 'skill_id')
                       )


class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(64))
    categories = db.relationship('Category', secondary=skills_category, backref=db.backref('skills', lazy='dynamic'))
    # users = db.relationship('User', secondary=user_skills, backref=db.backref('skills', lazy='dynamic'))

    def to_json(self):
        json_skill = {
            'name': self.name,
            'description': self.description,
            'categories': self.categories,
            'category_count': len(self.categories),
            'users': self.users,
            'user_count': len(self.users),
        }
        return json_skill

    def __lt__(self, other):
        return self.name < other.name

    def __str__(self):
        return self.name

    def __repr__(self):
        return self.__str__()


group_memberships = db.Table('user_group',
                             db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
                             db.Column('group_id', db.Integer, db.ForeignKey('groups.id')),
                             )


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    description = db.Column(db.String(64))
    default = db.Column(db.Boolean, default=False, index=True)
    users = db.relationship('User', secondary=group_memberships, backref=db.backref('groups', lazy='dynamic'))

    administrative_groups = ['Administrator']

    @classmethod
    def get_admin_users(cls):
        admin_user_list = []
        for admin_group in cls.groups_from_list(cls.administrative_groups):
            for user in admin_group.users:
                if user not in admin_user_list:
                    admin_user_list.append(user)
        return admin_user_list

    @classmethod
    def groups_from_list(cls, group_list):
        return cls.query.filter(cls.name.in_(group_list))

    def to_json(self):
        json_group = {
            'name': self.name,
            'description': self.description,
            'default': self.default,
            'users': self.users,
            'user_count': len(self.users),
        }
        return json_group

    def __repr__(self):
        return '<Group %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    username = db.Column(db.String(64), unique=True, index=True)
    password_hash = db.Column(db.String(128))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    confirmed = db.Column(db.Boolean, default=False)
    registered_on = db.Column(db.DateTime(), default=datetime.utcnow)
    approved = db.Column(db.Boolean, default=False)
    approved_on = db.Column(db.DateTime())
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    # Having a problem with self referencing keys and automatically mapping objects
    # approved_by_user = db.relationship('User', foreign_keys=approved_by)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    # approved_by_me = db.relationship('User.approved_by', backref='approved_by_me', lazy='dynamic')
    skills = db.relationship('Skill', secondary=user_skills, backref=db.backref('users', lazy='dynamic'))

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = hashlib.md5(self.email.encode('utf-8')).hexdigest()
        if self.username is None and self.email:
            self.username = self.email

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'reset': self.id})

    def reset_password(self, token, new_password):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('reset') != self.id:
            return False
        self.password = new_password
        db.session.add(self)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = Serializer(current_app.config['SECRET_KEY'], expiration)
        return s.dumps({'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        db.session.add(self)
        return True

    @property
    def is_administrator(self):
        return bool(self.in_groups(Group.administrative_groups))

    def in_groups(self, group_list, require_all=False):
        group_match = []
        for group in Group.groups_from_list(group_list):
            if group in self.groups:
                group_match.append(group)
            elif require_all:
                return False
        return group_match

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar(self, size=100, default='identicon', rating='g'):
        if request.is_secure:
            url = 'https://secure.gravatar.com/avatar'
        else:
            url = 'http://www.gravatar.com/avatar'
        hash = self.avatar_hash or hashlib.md5(
            self.email.encode('utf-8')).hexdigest()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def to_json(self):
        json_user = {
            'username': self.username,
            'registered_on': str(self.registered_on),
            'last_seen': str(self.last_seen),
        }
        return json_user

    def generate_auth_token(self, expiration):
        s = Serializer(current_app.config['SECRET_KEY'],
                       expires_in=expiration)
        return s.dumps({'id': self.id}).decode('ascii')

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token)
        except:
            return None
        return User.query.get(data['id'])

    def send_message(self, recipient_list, title, message):
        if isinstance(recipient_list, int):
            recipient_list = [recipient_list]
        for recipient in recipient_list:
            notification = Notification()
            notification.title = title
            notification.message = message
            notification.created_by = self.id
            notification.sent_to = recipient.id
            db.session.add(notification)
        db.session.commit()

    @property
    def display_name(self):
        if self.first_name and self.last_name:
            name = '{} {}'.format(self.first_name, self.last_name).strip()
        elif self.username:
            name = self.username
        else:
            name = self.email
        return name

    def __str__(self):
        return self.display_name

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    pass


login_manager.anonymous_user = AnonymousUser


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

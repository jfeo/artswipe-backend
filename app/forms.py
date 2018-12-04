from flask_security import RegisterForm
from flask_security.forms import Required
from wtforms import StringField


class ArtswipeRegisterForm(RegisterForm):
    first_name = StringField('First Name', [Required()])
    last_name = StringField('Last Name', [Required()])

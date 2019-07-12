# cookbook/ingredients/schema.py
import requests
import json
import graphene
from graphene import relay, ObjectType
from graphene_django import DjangoObjectType
from graphene_django.converter import convert_django_field_with_choices
from graphene_django.filter import DjangoFilterConnectionField
from graphql_relay.node.node import from_global_id

from .models import Note
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from rest_framework.authtoken.models import Token

# Exceptions
from graphql import GraphQLError


# Graphene will automatically map the Category model's fields onto the CategoryNode.
# This is configured in the CategoryNode's Meta class (as you can see below)

###########
# Queries #
###########

class NoteNode(DjangoObjectType):
    class Meta:
        model = Note
        filter_fields = ['title', 'content', 'color', 'pinned']
        interfaces = (relay.Node, )

    @classmethod
    def get_node(cls, info, id):
        # get object by provided id
        try:
            note = cls._meta.model.objects.get(id=id)
        except cls._meta.model.DoesNotExist:
            return None
        # check the ownership
        if info.context.user == note.owner:
            return note
        # different owner. Not allowed
        return GraphQLError("Access denied")


class UserNode(DjangoObjectType):
    class Meta:
        model = User
        filter_fields = ['username']
        exclude_fields = ('password', 'is_superuser', 'is_staff', 'note_set')
        interfaces = (relay.Node, )

  
class Query(object):
    token_is_valid = graphene.Boolean(key=graphene.String())
    note = relay.Node.Field(NoteNode)
    all_notes = DjangoFilterConnectionField(NoteNode)
    profile = graphene.Field(UserNode)
    all_colors = graphene.List(graphene.String)

    def resolve_token_is_valid(self, info, key):
        # Check if the token for a user exist and is valid
        try:
            Token.objects.get(key=key)
        except Token.DoesNotExist:
            return False
        return True

    def resolve_all_notes(self, info, **kwargs):
        # context will reference to the Django request
        if info.context.user.is_authenticated:
            return Note.objects.filter(owner=info.context.user)
        else:
            return Note.objects.none()

    def resolve_profile(self, info):
        if info.context.user.is_authenticated:
            print("return profiles")
            return User.objects.get(username=info.context.user)
        else:
            return GraphQLError("You are not authenticated. Please login first")

    def resolve_all_colors(self, info):
        colors = []
        for color in Note.COLOR_CHOICES:
            colors.append(color[0])
        return colors


#############
# Mutations #
#############

class AddNote(relay.ClientIDMutation):

    class Input:
        title = graphene.String(required=False)
        content = graphene.String(required=False)

    new_note = graphene.Field(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if info.context.user.is_authenticated:
            note = Note.objects.create(owner=info.context.user, **input)
            return AddNote(new_note=note)            
        else:
            return GraphQLError("You are not authenticated. Please login first")


class UpdateNotesColor(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        new_color = graphene.String(required=True)

    new_color = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if info.context.user.is_authenticated:
            local_id = from_global_id(input['id'])[1]
            try:
                note = Note.objects.get(id=local_id, owner=info.context.user)
            except Note.DoesNotExist:
                return None
            note.color = input['new_color']
            note.save()
            return UpdateNotesColor(input['new_color'])
        else:
            return GraphQLError("You are not authenticated. Please login first")


class UpdateNote(relay.ClientIDMutation):
    class Input:
        id = graphene.ID(required=True)
        color = graphene.String()
        title = graphene.String()
        content = graphene.String()
        pinned = graphene.Boolean()
        order = graphene.Int()

    new_note = graphene.Field(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if info.context.user.is_authenticated:
            local_id = from_global_id(input['id'])[1]
            input.pop('id', None)
            try:
                notes = Note.objects.filter(id=local_id, owner=info.context.user)
            except Note.DoesNotExist:
                return None
            if 'color' in input:
                input['color'] = Color.objects.get(label=input['color'])
            notes.update(**input)
            return UpdateNote(notes[0])
        else:
            return GraphQLError("You are not authenticated. Please login first")


class DeleteNotes(relay.ClientIDMutation):
    class Input:
        ids = graphene.List(graphene.ID, required=True)

    deleted_notes = graphene.List(NoteNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if info.context.user.is_authenticated:
            local_ids = [from_global_id(i)[1] for i in input['ids']]
            try:
                notes = Note.objects.filter(id__in=local_ids, owner=info.context.user)
            except Note.DoesNotExist:
                return None
            snapshot = list(notes)
            Note.objects.fill_gaps(notes)
            notes.delete()
            return DeleteNotes(snapshot)
        else:
            return GraphQLError("You are not authenticated. Please login first")


class SwitchPinNotes(relay.ClientIDMutation):
    class Input:
        ids = graphene.List(graphene.ID, required=True)
        action = graphene.String(required=True)

    action = graphene.String()
    pinned_unpinned_notes = graphene.List(NoteNode)
    prev_pinned_status = graphene.List(graphene.Boolean)
    cur_pinned_status = graphene.List(graphene.Boolean)
    prev_order = graphene.List(graphene.Int)
    cur_order = graphene.List(graphene.Int)

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if info.context.user.is_authenticated:
            local_ids = [from_global_id(i)[1] for i in input['ids']]
            try:
                notes = Note.objects.filter(id__in=local_ids, owner=info.context.user)
            except Note.DoesNotExist:
                return None
            prevOrder = []
            prevPinnedStatus = []
            for index, note in enumerate(notes):
                prevOrder.append(note.order)
                prevPinnedStatus.append(note.pinned)
                if input['action'] == "pin":
                    Note.objects.pin(note)
                else:
                    Note.objects.unpin(note)

            curPinnedStatus = [note.pinned for note in notes]
            curOrder = [note.order for note in notes]

            return SwitchPinNotes(input['action'], notes, prevPinnedStatus, curPinnedStatus, prevOrder, curOrder)
        else:
            return GraphQLError("You are not authenticated. Please login first")


class ReorderNote(relay.ClientIDMutation):
    """ Reorder note with move model's manager """
    class Input:
        id = graphene.ID(required=True)
        new_order = graphene.Int(required=True)

    new_note = graphene.Field(NoteNode)
    new_order = graphene.Int()
    old_order = graphene.Int()
    pinned = graphene.Boolean()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        if info.context.user.is_authenticated:
            local_id = from_global_id(input['id'])[1]
            try:
                note = Note.objects.get(id=local_id, owner=info.context.user)
            except Note.DoesNotExist:
                return None

            old_order = note.order
            new_order = input['new_order']
            Note.objects.move(note, new_order)
            return ReorderNote(note, new_order, old_order, note.pinned)
        else:
            return GraphQLError("You are not authenticated. Please login first")


class Login(relay.ClientIDMutation):
    class Input:
        username = graphene.String(required=True)
        password = graphene.String(required=True)

    key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = {
            'username': input['username'],
            'password': input['password']
        }
        response = requests.post(f"{Site.objects.get_current().domain}/rest-auth/login/", data=data)
        data = json.loads(response.text)
        if response.status_code == 200:
            return Login(data['key'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class Logout(relay.ClientIDMutation):
    class Input:
        key = graphene.String(required=True)

    detail = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        response = requests.post(
            f"{Site.objects.get_current().domain}/rest-auth/logout/",
            headers={'authorization': f"Token {input['key']}"})
        if response.status_code == 200:
            data = json.loads(response.text)
            return Logout(data['detail'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class AuthWithFacebook(relay.ClientIDMutation):
    class Input:
        access_token = graphene.String(required=True)
        # code = graphene.String()

    key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        print('input', input)
        data = {
            'access_token': input['access_token'],
        }
        response = requests.post(f"{Site.objects.get_current().domain}/rest-auth/facebook/", data=data)
        data = json.loads(response.text)
        if response.status_code == 200:
            return AuthWithFacebook(data['key'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class AuthWithGitHub(relay.ClientIDMutation):
    class Input:
        code = graphene.String(required=True)

    key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = {'code': input['code'],}
        response = requests.post(f"{Site.objects.get_current().domain}/rest-auth/github/", data=data)
        data = json.loads(response.text)
        if response.status_code == 200:
            return AuthWithGitHub(data['key'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class AuthWithTwitter(relay.ClientIDMutation):
    class Input:
        code = graphene.String(required=True)

    key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = {'code': input['code'],}
        response = requests.post(f"{Site.objects.get_current().domain}/rest-auth/twitter/", data=data)
        data = json.loads(response.text)
        if response.status_code == 200:
            return AuthWithTwitter(data['key'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class Registration(relay.ClientIDMutation):
    class Input:
        username = graphene.String(required=True)
        email = graphene.String(required=True)
        password1 = graphene.String(required=True)
        password2 = graphene.String(required=True)

    key = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = {
            'username': input['username'],
            'email': input['email'],
            'password1': input['password1'],
            'password2': input['password2'],
        }
        response = requests.post(
            f"{Site.objects.get_current().domain}/rest-auth/registration/", data=data
        )
        if response.status_code != 400:
            data = json.loads(response.text)
            return Registration(data['key'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class ConfirmEmail(relay.ClientIDMutation):
    class Input:
        key = graphene.String(required=True)

    detail = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = { 'key': input['key'] }
        response = requests.post(
            f"{Site.objects.get_current().domain}/rest-auth/registration/verify-email/", 
            data=data
        )
        if response.status_code != 400:
            data = json.loads(response.text)
            return ConfirmEmail(data['detail'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class PasswordReset(relay.ClientIDMutation):
    class Input:
        email = graphene.String(required=True)

    detail = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = { 'email': input['email'] }
        response = requests.post(
            f"{Site.objects.get_current().domain}/rest-auth/password/reset/", data=data
        )
        if response.status_code == 200:
            data = json.loads(response.text)
            return PasswordReset(data['detail'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class PasswordResetConfirm(relay.ClientIDMutation):
    class Input:
        uid = graphene.String(required=True)
        token = graphene.String(required=True)
        new_password1 = graphene.String(required=True)
        new_password2 = graphene.String(required=True)

    detail = graphene.String()

    @classmethod
    def mutate_and_get_payload(cls, root, info, **input):
        data = { 
            'uid': input['uid'],
            'token': input['token'],
            'new_password1': input['new_password1'],
            'new_password2': input['new_password2'],
        }
        response = requests.post(
            f"{Site.objects.get_current().domain}/rest-auth/password/reset/confirm/", data=data
        )
        if response.status_code == 200:
            data = json.loads(response.text)
            return PasswordResetConfirm(data['detail'])
        elif response.status_code == 400:
            return GraphQLError(response.text)
        else:
            return None


class Mutation(ObjectType):
    login = Login.Field()
    logout = Logout.Field()
    auth_with_facebook = AuthWithFacebook.Field()
    auth_with_github = AuthWithGitHub.Field()
    registration = Registration.Field()
    confirm_email = ConfirmEmail.Field()
    password_reset = PasswordReset.Field()
    password_reset_confirm = PasswordResetConfirm.Field()
    add_note = AddNote.Field()
    update_notes_color = UpdateNotesColor.Field()
    update_note = UpdateNote.Field()
    delete_notes = DeleteNotes.Field()
    switch_pin_notes = SwitchPinNotes.Field()
    reorder_note = ReorderNote.Field()

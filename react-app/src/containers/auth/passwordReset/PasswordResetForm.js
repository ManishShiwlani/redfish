import React from 'react';
import { Form, Field } from 'formik';
import FormikMaterialTextField from '../FormikMaterialTextField'
import FormWrapper from '../FormWrapper'
import Button from '@material/react-button';
import { Link } from "react-router-dom";
import { endpoints } from '../../AutoRouter'

const theme = {
  background: '#f0f0f0',
}

class PasswordResetForm extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      passwordVisibilityCondition: false,
    }
    this.switchPasswordVisibility = this.switchPasswordVisibility.bind(this)
  }
  switchPasswordVisibility() {
    this.setState({
      passwordVisibilityCondition: this.state.passwordVisibilityCondition ? false : true
    })
  }
  render() {
    const {status, touched, isSubmitting, errors} = this.props
    return (
      <FormWrapper theme={theme}>
        <Form>
          <h3>Reset password</h3>
          <Field
            id="email"
            label="Email address"
            name="email"
            type="email"
            component={FormikMaterialTextField}
          />
          <Button type="submit" className="form-button" disabled={isSubmitting}>
            Reset password
          </Button>
          <span>{status && status.non_field_errors}</span>
        </Form>
      </FormWrapper>
    )
  }
}

export default PasswordResetForm
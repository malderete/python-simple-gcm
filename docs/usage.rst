=====
Usage
=====

To use python-simple-gcm in a project::

    import simplegcm

    sender = simplegcm.Sender(api_key='your_api_key')
    r_ids = ['ABC', 'HJK']
    data = {'score': 5.1}
    opt = {'dry_run': True}
    message = simplegcm.Message(registration_ids=r_ids,
                                data=data, options=opt)
    ret = sender.send(message)
    retry_msg = ret.get_retry_message()
    if retry_msg:
        print('Retry')
        ret = g.send(retry_msg)
    else:
        print('All sent!')


Process the results::

    result = g.send(m)
    # Update the token because GCM told us we sent some old tokens.
    for reg_id, new_token in result.canonicals.items():
        update_device_token(reg_id, new_token)

    # Clean the tokens because are not registered in our app.
    for reg_id i result.unregistered:
        remove_token(reg_id)

In the example above 'update_device_token' and 'remove_token' show the idea behind the result processing. Those are not part of python-simple-gcm.

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

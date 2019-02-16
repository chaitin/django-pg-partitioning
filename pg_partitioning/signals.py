from django.dispatch import Signal

post_create_partition = Signal(providing_args=["partition_log"])
"""Sent when a partition is created.
"""
post_attach_partition = Signal(providing_args=["partition_log"])
"""Sent when a partition is attached.
"""
post_detach_partition = Signal(providing_args=["partition_log"])
"""Sent when a partition is detached.
"""

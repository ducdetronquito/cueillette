
def remove_class(element, class_name: str) -> None:
    for tag in element.find_class(class_name):
        tag.getparent().remove(tag)

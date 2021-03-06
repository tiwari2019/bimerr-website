import rdflib
from rdflib.serializer import Serializer
import json
import os
import re
import argparse


def find_ontology_element(element_uri, ont_jsonld):

    """
    Function to find an ontological element whether it is a concept,
    relation or attribute

    :param element_uri: Uri of the element we want to find
    :param ont_jsonld: ontology serialized as JSON-LD
    :return: the element dictionary within the JSON-LD structure.
    """

    for element in ont_jsonld:
        if element["@id"] == element_uri:
            break
    return element

def get_classes(ont_jsonld):

    """
    Function to find all the classes inside an jsonld owl serialization.

    :param ont_jsonld: ontology serialized as JSON-LD
    :return: List of URI's of all the classes in the ontology
    """

    total_concepts = []
    for element in ont_jsonld:
        try:
            # Classes have only one element inside the list "@type"
            type_uri = element["@type"][0]
            type = type_uri[type_uri.find("#") + 1:]
            # The "_" comparison avoids the inclusion of blank nodes in the list
            if type == "Class" and element["@id"][0] != "_":
                total_concepts.append(element["@id"])
        except:
            continue
    return total_concepts

def enrich_model(ont_jsonld, metadata):

    """
    Funtion to merge an ontology model from some domain and a enriched model of the same domain
    but with additional metdata annotations. The enriched model just contains these extra annotations.

    :param ont_jsonld: ontological model serialized as JSON-LD
    :param metadata: enriched ontological model serialized as JSON-LD
    :return: a unified ontological model with the original information from the domain and
            the extra annotations.
    """

    ann_uris, _ = get_annotation_property_uris()

    for meta_element in metadata:

        # Metadata extraction from the metadata ontology
        metadata_extracted = extract_elem_metadata(meta_element)

        # Metadata population on the original ontology
        for ont_element in ont_jsonld:
            if meta_element["@id"] == ont_element["@id"]:

                type_uri = ont_element["@type"][0]
                type = type_uri[type_uri.find("#") + 1:]

                ont_element[ann_uris["standard"]] = [{"@value": metadata_extracted["standard"]}]
                ont_element[ann_uris["added"]] = [{"@value": metadata_extracted["date_added"]}]
                ont_element[ann_uris["deprecated"]] = [{"@value": metadata_extracted["date_deprecated"]}]
                ont_element[ann_uris["version"]] = [{"@value": metadata_extracted["version"]}]

                # The following metadata fields are only used by children elements
                if type != "Class":
                    ont_element[ann_uris["ordered"]] = [{"@value": metadata_extracted["ordered"]}]
                    ont_element[ann_uris["sensitive"]] = [{"@value": metadata_extracted["sensitive"]}]
                    ont_element[ann_uris["transformation"]] = [{"@value": metadata_extracted["transformation"]}]
                    ont_element[ann_uris["measureType"]] = [{"@value": metadata_extracted["measurementType"]}]
                    ont_element[ann_uris["measureUnit"]] = [{"@value": metadata_extracted["measurementUnit"]}]
                    ont_element[ann_uris["timeZone"]] = [{"@value": metadata_extracted["timeZone"]}]
                    ont_element[ann_uris["codeList"]] = [{"@value": metadata_extracted["codeList"]}]
                    ont_element[ann_uris["codeType"]] = [{"@value": metadata_extracted["codeType"]}]
                break

    return ont_jsonld

def get_annotation_property_uris():

    """
    Generate all the prefixes and annotation properties needed
    :return:
            annotations: dictionary with all the annotation properties
            prefixes: dictionary with all the prefixes
    """

    annotations = {}
    prefixes = {}

    prefixes["rdfs"] = "http://www.w3.org/2000/01/rdf-schema#"
    prefixes["rdf"] = "http://www.w3.org/1999/02/22-rdf-syntax-ns#"
    prefixes["dc"] = "http://purl.org/dc/elements/1.1/"
    prefixes["owl"] = "http://www.w3.org/2002/07/owl#"
    prefixes["metadata"] = "http://bimerr.iot.linkeddata.es/def/metadata#"

    annotations["definition"] = prefixes["rdfs"] + "comment"
    annotations["terms"] = prefixes["rdfs"] + "label"
    annotations["standard"] = prefixes["metadata"] + "isDefinedByStandard"
    annotations["added"] = prefixes["dc"] + "created"
    annotations["deprecated"] = prefixes["metadata"] + "deprecated"
    annotations["version"] = prefixes["owl"] + "versionInfo"
    annotations["ordered"] = prefixes["metadata"] + "ordered"
    annotations["sensitive"] = prefixes["metadata"] + "sensitive"
    annotations["transformation"] = prefixes["metadata"] + "transformation"
    annotations["measureType"] = prefixes["metadata"] + "measurementType"
    annotations["measureUnit"] = prefixes["metadata"] + "measurementUnit"
    annotations["timeZone"] = prefixes["metadata"] + "timeZone"
    annotations["codeList"] = prefixes["metadata"] + "codeList"
    annotations["codeType"] = prefixes["metadata"] + "codeType"

    return annotations, prefixes

def populate_datamodel_elements(data_model_element, metadata, facet=False):

    """
    Populate the data model element with all the metadata needed
    :param data_model_element: dictionary with the data model element selected
    :param metadata: dictionary with all the metadata extracted from the ontology
    :param facet: boolean flag to indicate that the element is a children and require the
            population of extra annotations
    :return: dictionary with the data model element populated
    """

    if facet == False:
        data_model_element["definition"] = metadata["definition"]
        data_model_element["related_terms"] = [metadata["related_terms"]]
        data_model_element["standards"] = [metadata["standard"]]
        data_model_element["date_added"] = metadata["date_added"]
        data_model_element["date_deprecated"] = metadata["date_deprecated"]
        data_model_element["version"] = metadata["version"]

    else:
        data_model_element["ordered"] = metadata["ordered"]
        data_model_element["sensitive"] = metadata["sensitive"]
        data_model_element["transformation"] = metadata["transformation"]
        data_model_element["measurementType"] = metadata["measurementType"]
        data_model_element["measurementUnit"] = metadata["measurementUnit"]
        data_model_element["timeZone"] = metadata["timeZone"]
        data_model_element["codeList"] = metadata["codeList"]
        data_model_element["codeType"] = metadata["codeType"]

    return data_model_element

def extract_elem_metadata(element):

    ann, _ = get_annotation_property_uris()
    annotations_extracted = {}

    # Metadata extraction from the metadata ontology
    definition = element[ann["definition"]][0]["@value"] if ann["definition"] in element else None
    related_terms = element[ann["terms"]][0]["@value"] if ann["terms"] in element else None
    try:
        standard = element[ann["standard"]][0]["@value"] if ann["standard"] in element else None
    except:
        standard = element[ann["standard"]][0]["@id"] if ann["standard"] in element else None
    date_added = element[ann["added"]][0]["@value"] if ann["added"] in element else None
    date_deprecated = element[ann["deprecated"]][0]["@value"] if ann["deprecated"] in element else None
    version = element[ann["version"]][0]["@value"] if ann["version"] in element else None
    ordered = element[ann["ordered"]][0]["@value"] if ann["ordered"] in element else None
    sensitive = element[ann["sensitive"]][0]["@value"] if ann["sensitive"] in element else None
    transformation = element[ann["transformation"]][0]["@value"] if ann["transformation"] in element else None
    measurementType = element[ann["measureType"]][0]["@value"] if ann["measureType"] in element else None
    measurementUnit = element[ann["measureUnit"]][0]["@value"] if ann["measureUnit"] in element else None
    timeZone = element[ann["timeZone"]][0]["@value"] if ann["timeZone"] in element else None
    codeList = element[ann["codeList"]][0]["@value"] if ann["codeList"] in element else None
    codeType = element[ann["codeType"]][0]["@value"] if ann["codeType"] in element else None

    annotations_extracted["definition"] = definition
    annotations_extracted["related_terms"] = related_terms
    annotations_extracted["standard"] = standard
    annotations_extracted["date_added"] = date_added
    annotations_extracted["date_deprecated"] = date_deprecated
    annotations_extracted["version"] = version
    annotations_extracted["ordered"] = ordered
    annotations_extracted["sensitive"] = sensitive
    annotations_extracted["transformation"] = transformation
    annotations_extracted["measurementType"] = measurementType
    annotations_extracted["measurementUnit"] = measurementUnit
    annotations_extracted["timeZone"] = timeZone
    annotations_extracted["codeList"] = codeList
    annotations_extracted["codeType"] = codeType

    return annotations_extracted

def load_ontology(ontology_path):

    g = rdflib.Graph()
    g.parse(ontology_path, format='ttl')
    jsonld_model = g.serialize(format='json-ld', indent=4).decode()
    jsonld_model = json.loads(jsonld_model)

    return jsonld_model

def o2dm_conversion(ontology_path, output_datamodel_path=None):

    ont_ttl_filename = re.split(r'/', ontology_path)[-1]
    ont_prefix = ont_ttl_filename[:ont_ttl_filename.find("_")]
    metadata_jsonld = load_ontology(ontology_path)
    data_model = {}

    ann_uris, pref_uris = get_annotation_property_uris()

    for element in metadata_jsonld:
        if pref_uris["owl"] + "imports" in element:
            imported_ont = element[pref_uris["owl"] + "imports"][0]["@id"]
            break

    ont_jsonld = load_ontology(imported_ont[:-1]+"/ontology.ttl")
    ont_enriched_jsonld = enrich_model(ont_jsonld, metadata_jsonld)
    concepts = get_classes(ont_enriched_jsonld)

    for concept_uri in concepts:

        concept_name = concept_uri[concept_uri.find("#")+1:]
        element = find_ontology_element(concept_uri, ont_enriched_jsonld)

        concept_metadata = extract_elem_metadata(element)
        data_model[concept_name] = {}
        populate_datamodel_elements(data_model[concept_name], concept_metadata)
        superclasses = element[pref_uris["rdfs"] + "subClassOf"] if pref_uris["rdfs"] + "subClassOf" in element else []
        data_model[concept_name]["children"] = {}

        for superclass in superclasses:
            superclass_uri = superclass["@id"]
            superclass_name = superclass_uri[superclass_uri.find("#") + 1:]
            superclass_element = find_ontology_element(superclass_uri, ont_enriched_jsonld)
            superclass_type = superclass_element["@type"][0]
            superclass_type_name = superclass_type[superclass_type.find("#") + 1:]

            if superclass_type_name != "Restriction":
                continue

            property_uri = superclass_element[pref_uris["owl"] + "onProperty"][0]["@id"]
            property_element = find_ontology_element(property_uri, ont_enriched_jsonld)
            property_types = property_element["@type"]
            property_name = property_uri[property_uri.find("#") + 1:]

            property_metadata = extract_elem_metadata(property_element)
            data_model[concept_name]["children"][property_name] = {}
            populate_datamodel_elements(data_model[concept_name]["children"][property_name], property_metadata)

            if pref_uris["owl"] + "someValuesFrom" in superclass_element:
                datatype = superclass_element[pref_uris["owl"] + "someValuesFrom"][0]["@id"]
            elif pref_uris["owl"] + "allValuesFrom" in superclass_element:
                datatype = superclass_element[pref_uris["owl"] + "allValuesFrom"][0]["@id"]
            else:
                datatype = superclass_element[pref_uris["owl"] + "onClass"][0]["@id"]

            datatype = datatype[datatype.find("#") + 1:]

            if pref_uris["owl"] + "FunctionalProperty" in property_types:
                data_model[concept_name]["children"][property_name]["facet"] = {"cardinalityMax": 1}
            elif pref_uris["owl"] + "maxQualifiedCardinality" in superclass_element:
                max_cardinality = superclass_element[pref_uris["owl"] + "maxQualifiedCardinality"][0]["@value"]
                data_model[concept_name]["children"][property_name]["facet"] = {"cardinalityMax": max_cardinality}
            else:
                data_model[concept_name]["children"][property_name]["facet"] = {"cardinalityMax": None}

            populate_datamodel_elements(data_model[concept_name]["children"][property_name]["facet"],
                                        property_metadata, facet=True)

            if pref_uris["owl"] + "ObjectProperty" in property_types:
                data_model[concept_name]["children"][property_name]["type"] = {"$ref": "#/" + datatype}
            else:
                data_model[concept_name]["children"][property_name]["type"] = datatype

    for concept_uri in concepts:

        concept_name = concept_uri[concept_uri.find("#")+1:]
        element = find_ontology_element(concept_uri, ont_enriched_jsonld)
        superclasses = element[pref_uris["rdfs"] + "subClassOf"] if pref_uris["rdfs"] + "subClassOf" in element else []

        for superclass in superclasses:
            superclass_uri = superclass["@id"]
            superclass_name = superclass_uri[superclass_uri.find("#") + 1:]
            superclass_element = find_ontology_element(superclass_uri, ont_enriched_jsonld)
            superclass_type = superclass_element["@type"][0]
            superclass_type_name = superclass_type[superclass_type.find("#") + 1:]

            if superclass_type_name != "Class":
                continue

            superclass_children = data_model[superclass_name]["children"]

            for key, element in superclass_children.items():
                data_model[concept_name]["children"][key] = element

    if output_datamodel_path:
        with open(output_datamodel_path, "w") as f:
            json.dump(data_model, f, indent=4, separators=(',', ': '))

    return data_model

if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Ontology to data model conversion")
    parser.add_argument("ontology_path", help="Full path to the ontology model")
    parser.add_argument("datamodel_output_path", help="Full path to the output data model")
    args = parser.parse_args()

    o2dm_conversion(args.ontology_path, args.datamodel_output_path)
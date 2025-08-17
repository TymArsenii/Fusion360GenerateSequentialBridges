# Author - Mirza Cenanovic
# Description - Create support geometry for overhanging holes when 3D printing.
# Also known as sequential bridging

import adsk.core, adsk.fusion, adsk.cam, traceback
import time

# the depth of the extrusions
extrusionAmount = ("-0.5 mm", "-0.25 mm")


debug = False
#ui = None

def disp(ui,msg):
    print(msg)
    if isinstance(msg, str):
        adsk.core.Application.log(msg)
        if not debug:
            ui.messageBox(msg)

def ExtrudeProfiles(rootComp, outerProfiles, innerProfiles):
    extrudes = rootComp.features.extrudeFeatures
    fullDistance = adsk.core.ValueInput.createByString(extrusionAmount[0])
    halfDistance = adsk.core.ValueInput.createByString(extrusionAmount[1])
    extent_distance_half = adsk.fusion.DistanceExtentDefinition.create(halfDistance)
    extent_distance_full = adsk.fusion.DistanceExtentDefinition.create(fullDistance)

    extrudeInput = extrudes.createInput(outerProfiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudeInput.setOneSideExtent(extent_distance_half, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrude1 = extrudes.add(extrudeInput)

    extrudeInput = extrudes.createInput(innerProfiles, adsk.fusion.FeatureOperations.CutFeatureOperation)
    extrudeInput.setOneSideExtent(extent_distance_full, adsk.fusion.ExtentDirections.PositiveExtentDirection)
    extrude2 = extrudes.add(extrudeInput)    
    
    return (extrude1, extrude2)

def CreateSequentialBridges(ui, rootComp, face):
    #Create a sketch on the face
    sketch = rootComp.sketches.add(face)

    # Highligt entities for debugging
    # sels: adsk.core.Selections = ui.activeSelections
    # sels.clear()
    # sels.add(face)

    curves = sketch.sketchCurves
            
    disp(ui, curves.count)
    # Check if the proper geometry was selected
    if not curves.count >= 2:
        disp(ui, "One of the faces does not contain two curves!")
        return
    
    if curves.count == 2:
        if not hasattr(curves[0],"radius") or not hasattr(curves[1],"radius"):
            sketch.deleteMe()
            disp(ui,"This geometry is not supported")
            return
        #Hole geometry
        # Determine the inner and outer circles
        # c1 is the outer circle
        if curves[0].radius > curves[1].radius:
            c1 = curves[0]
            c2 = curves[1]
        else:
            c2 = curves[0]
            c1 = curves[1]

        R = c1.radius
        r = c2.radius
        
    elif curves.count == 7:
        if not hasattr(curves,"sketchCircles") or not hasattr(curves,"sketchLines"):
            sketch.deleteMe()
            disp(ui,"This geometry is not supported")
            return
        #Hex geometry
        c1 = curves.sketchCircles[0]
        r = c1.radius
        R = curves.sketchLines[0].length
    else:
        sketch.deleteMe()
        disp(ui,"This geometry is not supported")
        return

    cP = c1.centerSketchPoint
    xc = cP.geometry.x
    yc = cP.geometry.y
    zc = cP.geometry.z
    
    # Draw lines, the point below is in a local coordinate system
    # No trimming is needed thanks to Fusion360 automatic sketch profiling
    lines = sketch.sketchCurves.sketchLines
    lineW = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc-r, yc+R, zc-0), 
        adsk.core.Point3D.create(xc-r, yc-R, zc-0))
    lineE = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc+r, yc+R, zc-0), 
        adsk.core.Point3D.create(xc+r, yc-R, zc-0))
    lineN = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc-R, yc+r, zc-0), 
        adsk.core.Point3D.create(xc+R, yc+r, zc-0))
    lineS = lines.addByTwoPoints(
        adsk.core.Point3D.create(xc-R, yc-r, zc-0), 
        adsk.core.Point3D.create(xc+R, yc-r, zc-0))
    
    profiles = sketch.profiles

    innerProfiles = adsk.core.ObjectCollection.create()
    outerProfiles = adsk.core.ObjectCollection.create()

    #Arsenii'sTechnologies (fully constraining a skecth) ->
    # Draw center rectangle around all lines with coincident points
    min_x = min(xc - R, xc - r)
    max_x = max(xc + R, xc + r)
    min_y = min(yc - R, yc - r)
    max_y = max(yc + R, yc + r)

    pt1 = adsk.core.Point3D.create(min_x, min_y, zc)
    pt2 = adsk.core.Point3D.create(max_x, min_y, zc)
    pt3 = adsk.core.Point3D.create(max_x, max_y, zc)
    pt4 = adsk.core.Point3D.create(min_x, max_y, zc)

    rect_lines = []
    rect_lines.append(lines.addByTwoPoints(pt1, pt2))
    rect_lines.append(lines.addByTwoPoints(pt2, pt3))
    rect_lines.append(lines.addByTwoPoints(pt3, pt4))
    rect_lines.append(lines.addByTwoPoints(pt4, pt1))

    constraints = sketch.geometricConstraints

    constraints.addCoincident(rect_lines[0].endSketchPoint, rect_lines[1].startSketchPoint)
    constraints.addCoincident(rect_lines[1].endSketchPoint, rect_lines[2].startSketchPoint)
    constraints.addCoincident(rect_lines[2].endSketchPoint, rect_lines[3].startSketchPoint)
    constraints.addCoincident(rect_lines[3].endSketchPoint, rect_lines[0].startSketchPoint)

    # Make lines horizontal/vertical
    constraints.addHorizontal(lineN)
    constraints.addHorizontal(lineS)
    constraints.addVertical(lineE)
    constraints.addVertical(lineW)

    # Make internal lines tangent to the circle
    try:
        print(c2)
    except NameError:
        print("my_var is not accessible")

        constraints.addTangent(lineN, c1)
        constraints.addTangent(lineS, c1)
        constraints.addTangent(lineE, c1)
        constraints.addTangent(lineW, c1)
    else:
        print("my_var exists and is accessible")

        constraints.addTangent(lineN, c2)
        constraints.addTangent(lineS, c2)
        constraints.addTangent(lineE, c2)
        constraints.addTangent(lineW, c2)


    # Make rectangle sides horizontal/vertical
    constraints.addHorizontal(rect_lines[0])  # bottom
    constraints.addHorizontal(rect_lines[2])  # top
    constraints.addVertical(rect_lines[1])    # right
    constraints.addVertical(rect_lines[3])    # left

    # Make all sides equal (convert to square)
    constraints.addEqual(rect_lines[0], rect_lines[1])

    # Add a diagonal construction line
    diag_line = lines.addByTwoPoints(rect_lines[0].startSketchPoint, rect_lines[1].endSketchPoint)
    diag_line.isConstruction = True

    # Add a midpoint on a diagonal line
    mid_x = (rect_lines[0].startSketchPoint.geometry.x + rect_lines[1].endSketchPoint.geometry.x) / 2
    mid_y = (rect_lines[0].startSketchPoint.geometry.y + rect_lines[1].endSketchPoint.geometry.y) / 2
    diag_midpoint = sketch.sketchPoints.add(adsk.core.Point3D.create(mid_x, mid_y, zc))

    # Constrain the point to be the midpoint of the diagonal
    constraints = sketch.geometricConstraints
    constraints.addMidPoint(diag_midpoint, diag_line)

    # Make the diagonal midpoint coincident with the circle center
    constraints.addCoincident(diag_midpoint, c1.centerSketchPoint)

    # Add a dimension to one square side matching internal line length
    dims = sketch.sketchDimensions
    side_length = lineN.length
    dims.addDistanceDimension(
        rect_lines[0].startSketchPoint,
        rect_lines[0].endSketchPoint,
        adsk.fusion.DimensionOrientations.HorizontalDimensionOrientation,
        adsk.core.Point3D.create(xc, yc + R + 1, zc)  # place dimension slightly above
    )

    # Make internal lines endpoints coincident with square sides
    constraints.addCoincident(lineN.startSketchPoint, rect_lines[3])  # lineN left end -> left side
    constraints.addCoincident(lineN.endSketchPoint, rect_lines[1])    # lineN right end -> right side

    constraints.addCoincident(lineS.startSketchPoint, rect_lines[3])  # lineS left end -> left side
    constraints.addCoincident(lineS.endSketchPoint, rect_lines[1])    # lineS right end -> right side

    constraints.addCoincident(lineE.startSketchPoint, rect_lines[0])  # lineE bottom end -> bottom side
    constraints.addCoincident(lineE.endSketchPoint, rect_lines[2])    # lineE top end -> top side

    constraints.addCoincident(lineW.startSketchPoint, rect_lines[0])  # lineW bottom end -> bottom side
    constraints.addCoincident(lineW.endSketchPoint, rect_lines[2])    # lineW top end -> top side

    #<- Arsenii'sTechnologies




    # Highlight stuff for debugging
    #sels.clear
    
    for i in range(profiles.count):
        profile_i = profiles.item(i)
        bcx = abs( (profile_i.boundingBox.maxPoint.x + profile_i.boundingBox.minPoint.x)/2 - xc)
        bcy = abs( (profile_i.boundingBox.maxPoint.y + profile_i.boundingBox.minPoint.y)/2 - yc)
        if bcx < 1e-6 and bcy < 1e-6:
            continue
        if r > bcx and bcx > -r: 
            if r > bcy and bcy > -r:
                innerProfiles.add(profile_i)
                outerProfiles.add(profile_i)
                #sels.add(profile_i)
            else:
                outerProfiles.add(profile_i)
                #sels.add(profile_i)
    
    #Create extrusion
    ExtrudeProfiles(rootComp, outerProfiles, innerProfiles)        

def run(context):
    
    try:
        app = adsk.core.Application.get()
        ui  = app.userInterface
        design = app.activeProduct
        rootComp = design.rootComponent

        # Get user selected faces
        faces = []
        for selection in ui.activeSelections:
            selectedEnt = selection.entity
            #disp(ui,selectedEnt.objectType)
            if not selectedEnt.objectType == "adsk::fusion::BRepFace":
                disp(ui,"Not a BRepFace! Skipping.")
                continue
            faces.append(selectedEnt)    

        # What has the user selected?
        if len(faces) == 0:
            disp(ui,"Nothing selected!")

        # Loop through all user selected faces and do the magic
        for face in faces:
            CreateSequentialBridges(ui, rootComp, face)

    except:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
